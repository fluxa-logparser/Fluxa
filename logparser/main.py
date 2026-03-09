#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main - Log Router 系统启动文件

功能：模拟 Benchmark 的启动方式，对 data/loghub_2k 下的所有日志数据进行解析

使用说明：
    python main.py

输出：
    - 所有Dataset的解析结果
    - DeepParse_bechmark_result.csv（总体统计）
    - 各个Dataset的详细结果

作者：整合 BulkParse + DeepParse 的智能日志路由系统
"""

import sys
import os
import time
import pandas as pd
from datetime import datetime

# 导入 Log Router
from log_route import LogRouter
# 导入评估器
from utils import evaluator
# 导入准确率计算
import evaluate_final_results


# ============================================================================
# 工具函数
# ============================================================================

def _extract_fields_by_format(log_line, log_format, regex_patterns):
    """
    根据日志格式提取字段

    参数：
    - log_line: 原始日志行
    - log_format: 日志格式（如 "<Date> <Time> <Pid> <Level> <Component>: <Content>"）
    - regex_patterns: 正则表达式列表

    返回：字段字典
    """
    import re

    # 解析日志格式，提取字段名
    field_names = re.findall(r'<(\w+)>', log_format)

    # 先尝试简单的空格分割（适用于大多数情况）
    parts = log_line.split()
    fields = {}

    # 特殊处理：HDFS 格式 "<Date> <Time> <Pid> <Level> <Component>: <Content>"
    if 'Component' in field_names and 'Content' in field_names and ':' in log_line:
        # 按 ':' 分离 Component 和 Content
        before_colon = log_line.rsplit(':', 1)[0]
        after_colon = log_line.rsplit(':', 1)[1]

        # 提取 Component（冒号前的最后一部分）
        component_parts = before_colon.split()
        if 'Level' in field_names and len(component_parts) >= 5:
            fields['Date'] = component_parts[0] if 'Date' in field_names else ''
            fields['Time'] = component_parts[1] if 'Time' in field_names else ''
            fields['Pid'] = component_parts[2] if 'Pid' in field_names else ''
            fields['Level'] = component_parts[3] if 'Level' in field_names else ''
            fields['Component'] = ' '.join(component_parts[4:]) if 'Component' in field_names else ''
        else:
            fields['Component'] = before_colon.strip() if 'Component' in field_names else ''

        # 提取 Content
        fields['Content'] = after_colon.strip() if 'Content' in field_names else ''

        # 填充其他字段
        for field_name in field_names:
            if field_name not in fields:
                if len(parts) > field_names.index(field_name):
                    fields[field_name] = parts[field_names.index(field_name)]
                else:
                    fields[field_name] = ''

        return fields

    # 其他格式：尝试逐个匹配
    idx = 0
    for field_name in field_names:
        if idx >= len(parts):
            fields[field_name] = ''
            continue

        if field_name == 'Content':
            # Content 是剩余所有内容
            fields[field_name] = ' '.join(parts[idx:])
            break
        else:
            fields[field_name] = parts[idx]
            idx += 1

    # 填充缺失的字段
    for field_name in field_names:
        if field_name not in fields:
            fields[field_name] = ''

    return fields


# ============================================================================
# 配置所有Dataset
# ============================================================================

DATA_BASE = "../data/loghub_2k"
OUTPUT_DIR = "DeepParse_results"

# 所有Dataset配置（参考 BulkParse/benchmark.py）
DATASET_CONFIGS = {
    "HDFS": {
        "log_file": "HDFS/HDFS_2k.log",
        "log_format": "<Date> <Time> <Pid> <Level> <Component>: <Content>",
        "regex": [r"blk_-?\d+", r"(\d+\.){3}\d+(:\d+)?"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Hadoop": {
        "log_file": "Hadoop/Hadoop_2k.log",
        "log_format": "<Date> <Time> <Level> \[<Process>\] <Component>: <Content>",
        "regex": [r"(\d+\.){3}\d+"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Spark": {
        "log_file": "Spark/Spark_2k.log",
        "log_format": "<Date> <Time> <Level> <Component>: <Content>",
        "regex": [r"(\d+\.){3}\d+", r"\b[KGTM]?B\b", r"([\w-]+\.){2,}[\w-]+"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Zookeeper": {
        "log_file": "Zookeeper/Zookeeper_2k.log",
        "log_format": "<Date> <Time> - <Level>  \[<Node>:<Component>@<Id>\] - <Content>",
        "regex": [r"(/|)(\d+\.){3}\d+(:\d+)?"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "BGL": {
        "log_file": "BGL/BGL_2k.log",
        "log_format": "<Label> <Timestamp> <Date> <Node> <Time> <NodeRepeat> <Type> <Component> <Level> <Content>",
        "regex": [r"core\.\d+"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "HPC": {
        "log_file": "HPC/HPC_2k.log",
        "log_format": "<LogId> <Node> <Component> <State> <Time> <Flag> <Content>",
        "regex": [r"=\d+"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Thunderbird": {
        "log_file": "Thunderbird/Thunderbird_2k.log",
        "log_format": "<Label> <Timestamp> <Date> <User> <Month> <Day> <Time> <Location> <Component>(\[<PID>\])?: <Content>",
        "regex": [r"(\d+\.){3}\d+"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Windows": {
        "log_file": "Windows/Windows_2k.log",
        "log_format": "<Date> <Time>, <Level>                  <Component>    <Content>",
        "regex": [r"0x.*?\s"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Linux": {
        "log_file": "Linux/Linux_2k.log",
        "log_format": "<Month> <Date> <Time> <Level> <Component>(\[<PID>\])?: <Content>",
        "regex": [r"(\d+\.){3}\d+", r"\d{2}:\d{2}:\d{2}"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Android": {
        "log_file": "Android/Android_2k.log",
        "log_format": "<Date> <Time>  <Pid>  <Tid> <Level> <Component>: <Content>",
        "regex": [
            r"(/[\w-]+)+",
            r"([\w-]+\.){2,}[\w-]+",
            r"\b(\-?\+?\d+)\b|\b0[Xx][a-fA-F\d]+\b|\b[a-fA-F\d]{4,}\b",
        ],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "HealthApp": {
        "log_file": "HealthApp/HealthApp_2k.log",
        "log_format": "<Time>\|<Component>\|<Pid>\|<Content>",
        "regex": [],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Apache": {
        "log_file": "Apache/Apache_2k.log",
        "log_format": "\[<Time>\] \[<Level>\] <Content>",
        "regex": [r"(\d+\.){3}\d+"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Proxifier": {
        "log_file": "Proxifier/Proxifier_2k.log",
        "log_format": "\[<Time>\] <Program> - <Content>",
        "regex": [
            r"<\d+\ssec",
            r"([\w-]+\.)+[\w-]+(:\d+)?",
            r"\d{2}:\d{2}(:\d{2})*",
            r"[KGTM]B",
        ],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "OpenSSH": {
        "log_file": "OpenSSH/OpenSSH_2k.log",
        "log_format": "<Date> <Day> <Time> <Component> sshd\[<Pid>\]: <Content>",
        "regex": [r"(\d+\.){3}\d+", r"([\w-]+\.){2,}[\w-]+"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "OpenStack": {
        "log_file": "OpenStack/OpenStack_2k.log",
        "log_format": "<Logrecord> <Date> <Time> <Pid> <Level> <Component> \[<ADDR>\] <Content>",
        "regex": [r"((\d+\.){3}\d+,?)+", r"/.+?\s", r"\d+"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
    "Mac": {
        "log_file": "Mac/Mac_2k.log",
        "log_format": "<Month>  <Date> <Time> <User> <Component>\[<PID>\]( \(<Address>\))?: <Content>",
        "regex": [r"([\w-]+\.){2,}[\w-]+"],
        "sample_ratio": 0.1,
        "max_samples": 200,
    },
}


# ============================================================================
# 主函数
# ============================================================================

def main():
    """Main function: Parse all datasets"""

    print("=" * 80)
    print(" Log Router - Intelligent Log Parsing System")
    print(" Integrating BulkParse + DeepParse")
    print("=" * 80)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Statistics
    total_start_time = time.time()
    benchmark_results = []
    all_datasets = sorted(DATASET_CONFIGS.keys())

    print(f"\nProcessing {len(all_datasets)} datasets: {', '.join(all_datasets)}")

    # Process each dataset
    for idx, dataset in enumerate(all_datasets, 1):
        config = DATASET_CONFIGS[dataset]
        log_file_path = os.path.join(DATA_BASE, config["log_file"])

        # Check if file exists
        if not os.path.exists(log_file_path):
            print(f"[{idx}/{len(all_datasets)}] {dataset} - SKIP (file not found)")
            continue

        try:
            print(f"[{idx}/{len(all_datasets)}] {dataset}...", end='', flush=True)

            # Read log file
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_logs = [line.strip() for line in f if line.strip()]

            # Create router
            dataset_start_time = time.time()
            router = LogRouter(
                sampler_config={
                    'sampling_strategy': 'hybrid',
                    'sample_ratio': config['sample_ratio'],
                    'max_samples': config['max_samples'],
                    'regex': config['regex'],
                    'similarity_threshold': 0.5,
                },
                drain_config={
                    'similarity_threshold': 0.5,
                    'regex': config['regex'],
                },
                working_dir=os.path.join(OUTPUT_DIR, f"{dataset}_router")
            )

            # Initialize
            router.initialize_from_logs(all_logs, force_reinit=True)
            init_time = time.time() - dataset_start_time

            # Parse all data
            parse_start_time = time.time()
            results = router.route_and_parse_batch(all_logs)
            parse_time = time.time() - parse_start_time

            # Statistics
            drain_count = sum(1 for r in results if r['method'] == 'BulkParse')
            deep_parse_count = sum(1 for r in results if r['method'] == 'DeepParse')
            new_learned = router.stats['new_templates_learned']

            # Save results
            output_csv = os.path.join(OUTPUT_DIR, f"{dataset}_results.csv")
            import pandas as pd
            df_results = pd.DataFrame(results)
            df_results.to_csv(output_csv, index=False)

            # Record statistics
            benchmark_results.append({
                'Dataset': dataset,
                'Total_Logs': len(all_logs),
                'Initial_Templates': len(router.template_library),
                'Parsing_Time_Total': init_time + parse_time,
                'Init_Time': init_time,
                'Parse_Time': parse_time,
                'BulkParse_Count': drain_count,
                'DeepParse_Count': deep_parse_count,
                'BulkParse_Ratio': f"{drain_count/len(results)*100:.2f}%",
                'DeepParse_Ratio': f"{deep_parse_count/len(results)*100:.2f}%",
                'New_Templates': new_learned,
                'Avg_Speed': f"{parse_time/len(results):.4f}",
            })

            # Save router state
            router.save_state()

            print(f" OK ({len(results)} logs, {parse_time:.1f}s)")

        except Exception as e:
            print(f" ERROR: {e}")

            # Record failed dataset
            benchmark_results.append({
                'Dataset': dataset,
                'Total_Logs': 0,
                'Initial_Templates': 0,
                'Parsing_Time_Total': 0,
                'Init_Time': 0,
                'Parse_Time': 0,
                'BulkParse_Count': 0,
                'DeepParse_Count': 0,
                'BulkParse_Ratio': 'ERROR',
                'DeepParse_Ratio': 'ERROR',
                'New_Templates': 0,
                'Avg_Speed': 'ERROR',
            })

    # ============================================================================
    # Generate summary report
    # ============================================================================

    total_time = time.time() - total_start_time

    print("\n" + "=" * 80)
    print(f" All datasets completed in {total_time:.2f} seconds")
    print("=" * 80)

    # Generate summary table
    df_summary = pd.DataFrame(benchmark_results)
    df_summary.set_index('Dataset', inplace=True)

    # Save to CSV
    summary_csv = os.path.join(OUTPUT_DIR, "DeepParse_bechmark_result.csv")
    df_summary.to_csv(summary_csv, float_format="%.6f")

    # Print summary
    print("\n" + df_summary.to_string())

    # Aggregate statistics
    successful_datasets = df_summary[df_summary['BulkParse_Ratio'] != 'ERROR']

    if len(successful_datasets) > 0:
        total_logs = successful_datasets['Total_Logs'].sum()
        total_bulk_parse = successful_datasets['BulkParse_Count'].astype(int).sum()
        total_deep_parse = successful_datasets['DeepParse_Count'].astype(int).sum()
        total_new_templates = successful_datasets['New_Templates'].astype(int).sum()

        print(f"\nSummary: {len(successful_datasets)} datasets, {total_logs:,} logs")
        print(f"BulkParse: {total_bulk_parse:,} ({total_bulk_parse/total_logs*100:.1f}%)")
        print(f"DeepParse: {total_deep_parse:,} ({total_deep_parse/total_logs*100:.1f}%)")

    print("=" * 80)

if __name__ == '__main__':
    main()

if __name__ == '__main__':
    main()
