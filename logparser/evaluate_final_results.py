
import os
import pandas as pd
from collections import Counter

DATASETS = ["HDFS", "Android", "Apache", "BGL", "Hadoop", "HealthApp", "HPC",
            "Linux", "Mac", "OpenSSH", "OpenStack", "Proxifier", "Spark",
            "Thunderbird", "Windows", "Zookeeper"]

# Data paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, 'data', 'results')
CORRECTED_DIR = os.path.join(BASE_DIR, 'data', 'loghub_2k')
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')


def evaluatePA(groundtruth, result):
    """Calculate Parsing Accuracy"""
    length = len(result['template'])
    if length == 0:
        return 0

    correct = 0
    for i in range(length):
        gt_records = groundtruth[groundtruth['Content'] == result['log'][i]]
        if len(gt_records) > 0:
            gt_template = gt_records['EventTemplate'].values[0]
            if result['template'][i] == gt_template:
                correct += 1

    return correct / length


def build_template_dicts(groundtruth, result):
    """Build template dictionaries (shared by PTA and RTA) to avoid duplicate computation"""
    oracle_tem_dict = {}
    for idx in range(len(groundtruth)):
        gt_template = groundtruth.iloc[idx]['EventTemplate']
        gt_content = groundtruth.iloc[idx]['Content']
        if gt_template not in oracle_tem_dict:
            oracle_tem_dict[gt_template] = [gt_content]
        else:
            oracle_tem_dict[gt_template].append(gt_content)

    result_tem_dict = {}
    for idx in range(len(result)):
        result_template = result.iloc[idx]['template']
        result_log = result.iloc[idx]['log']
        if result_template not in result_tem_dict:
            result_tem_dict[result_template] = [result_log]
        else:
            result_tem_dict[result_template].append(result_log)

    return oracle_tem_dict, result_tem_dict


def evaluatePTA(oracle_tem_dict, result_tem_dict):
    """Calculate Precision Template Accuracy (using pre-built dictionaries)"""
    correct_num = 0
    for key in result_tem_dict.keys():
        if key in oracle_tem_dict:
            if Counter(oracle_tem_dict[key]) == Counter(result_tem_dict[key]):
                correct_num += 1

    return correct_num / len(result_tem_dict) if len(result_tem_dict) > 0 else 0


def evaluateRTA(oracle_tem_dict, result_tem_dict):
    """Calculate Recall Template Accuracy (using pre-built dictionaries)"""
    correct_num = 0
    for key in oracle_tem_dict.keys():
        if key in result_tem_dict:
            if Counter(oracle_tem_dict[key]) == Counter(result_tem_dict[key]):
                correct_num += 1

    return correct_num / len(oracle_tem_dict) if len(oracle_tem_dict) > 0 else 0


def evaluateGA(groundtruth, result):
    """Calculate Grouping Accuracy"""
    compared_list = result['log'].tolist()

    parsed_idx = []
    for idx, row in groundtruth.iterrows():
        if row['Content'] in compared_list:
            parsed_idx.append(idx)
            compared_list.remove(row['Content'])

    if len(parsed_idx) == 0:
        return 0

    groundtruth_filtered = groundtruth.loc[parsed_idx]

    groundtruth_dict = {}
    for idx, row in groundtruth_filtered.iterrows():
        if row['EventTemplate'] not in groundtruth_dict:
            groundtruth_dict[row['EventTemplate']] = [row['Content']]
        else:
            groundtruth_dict[row['EventTemplate']].append(row['Content'])

    result_dict = {}
    for idx, row in result.iterrows():
        if row['template'] not in result_dict:
            result_dict[row['template']] = [row['log']]
        else:
            result_dict[row['template']].append(row['log'])

    for key in groundtruth_dict.keys():
        groundtruth_dict[key].sort()

    for key in result_dict.keys():
        result_dict[key].sort()

    count = 0
    for parsed_group_list in result_dict.values():
        for gt_group_list in groundtruth_dict.values():
            if parsed_group_list == gt_group_list:
                count += len(parsed_group_list)
                break

    return count / len(result)


def calculate():

    benchmark_results = []

    for dataset in DATASETS:

        # Result file path
        result_file = os.path.join(RESULTS_DIR, f"2000_{dataset}_result.csv")

        # Corrected groundtruth path
        corrected_file = os.path.join(CORRECTED_DIR, dataset,
                                       f"{dataset}_2k.log_structured.csv")

        if not os.path.exists(result_file):

            continue

        if not os.path.exists(corrected_file):

            continue

        try:
            # Read data
            df_result = pd.read_csv(result_file)
            df_groundtruth = pd.read_csv(corrected_file)


            # Calculate four accuracy metrics (optimized: avoid duplicate dictionary construction)
            pa = evaluatePA(df_groundtruth, df_result)

            # Build template dictionaries (build once, shared by PTA and RTA)
            oracle_tem_dict, result_tem_dict = build_template_dicts(df_groundtruth, df_result)

            pta = evaluatePTA(oracle_tem_dict, result_tem_dict)
            rta = evaluateRTA(oracle_tem_dict, result_tem_dict)
            ga = evaluateGA(df_groundtruth, df_result)


            benchmark_results.append({
                'Dataset': dataset,
                'PA': pa,
                'PTA': pta,
                'RTA': rta,
                'GA': ga
            })

        except Exception as e:

            import traceback
            traceback.print_exc()

    # Calculate and display results (do not save CSV file)
    if len(benchmark_results) > 0:
        df_results = pd.DataFrame(benchmark_results)

        # Display detailed results
        df_display = df_results.copy()
        df_display.set_index('Dataset', inplace=True)

        # Calculate average accuracy
        avg_pa = df_results['PA'].mean()
        avg_pta = df_results['PTA'].mean()
        avg_rta = df_results['RTA'].mean()
        avg_ga = df_results['GA'].mean()

        print(f"\nAverage Accuracy:")
        print(f"PA:  {avg_pa:.6f}")
        print(f"PTA: {avg_pta:.6f}")
        print(f"RTA: {avg_rta:.6f}")
        print(f"GA:  {avg_ga:.6f}")
        print("="*80 + "\n")

        # Return average accuracy for main.py to call
        return {
            'avg_pa': avg_pa,
            'avg_pta': avg_pta,
            'avg_rta': avg_rta,
            'avg_ga': avg_ga
        }
    else:
        print("\n[Error] No dataset was successfully processed\n")
        return {
            'avg_pa': 0.0,
            'avg_pta': 0.0,
            'avg_rta': 0.0,
            'avg_ga': 0.0
        }


if __name__ == '__main__':
    calculate()
