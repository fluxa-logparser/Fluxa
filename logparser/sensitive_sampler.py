#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import hashlib
import pandas as pd
import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple, Set
import time


class SensitiveLogSampler:
    """
    Sensitive Log Sampler

    Filters representative samples from large-scale log data
    """

    def __init__(self,
                 sampling_strategy='drain',
                 sample_ratio=0.1,
                 max_samples=1000,
                 log_format='<Date> <Time> <Pid> <Level> <Component>: <Content>',
                 regex=None,
                 similarity_threshold=0.5):
        """
        Initialize sampler

        Parameters:
        - sampling_strategy: Sampling strategy ('drain', 'hash', 'embedding', 'hybrid')
        - sample_ratio: Sampling ratio (0.1 means 10%)
        - max_samples: Maximum number of samples
        - log_format: Log format
        - regex: List of regex patterns
        - similarity_threshold: Similarity threshold (for BulkParse)
        """
        self.sampling_strategy = sampling_strategy
        self.sample_ratio = sample_ratio
        self.max_samples = max_samples
        self.log_format = log_format
        self.regex = regex if regex else []
        self.similarity_threshold = similarity_threshold

        # Statistics
        self.stats = {
            'total_logs': 0,
            'unique_templates': 0,
            'selected_samples': 0,
            'processing_time': 0
        }

        # Template library
        self.templates = {}

    def _preprocess_log(self, log_message):
        """Preprocess log message"""
        processed = log_message.strip()

        # Apply regex substitutions
        for regex_pattern in self.regex:
            processed = re.sub(regex_pattern, '<*>', processed)

        return processed

    def _extract_content(self, log_line):
        """Extract Content part from log line"""
        # Simple implementation: extract based on log format
        # Assuming format: '<Date> <Time> <Pid> <Level> <Component>: <Content>'

        parts = log_line.split(': ', 1)
        if len(parts) > 1:
            return parts[1]
        return log_line

    def _get_log_hash(self, log_message):
        """Calculate hash value of log (for fast deduplication and classification)"""
        # Preprocess
        processed = self._preprocess_log(log_message)

        # Replace numbers and IPs with wildcards before calculating hash
        normalized = re.sub(r'\b\d+\b', '<NUM>', processed)
        normalized = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', normalized)
        normalized = re.sub(r'blk_[-]?\d+', 'blk_<ID>', normalized)

        # Calculate hash
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def _drain_based_sampling(self, log_messages: List[str]) -> List[str]:
        """
        BulkParse-based sampling strategy

        Uses BulkParse algorithm for fast clustering, selects representative samples from each cluster
        """
        print("\nUsing BulkParse strategy for sampling...")

        # Template dictionary: {template: [log list]}
        template_clusters = defaultdict(list)

        for log_msg in log_messages:
            # Preprocess
            content = self._extract_content(log_msg)
            processed = self._preprocess_log(content)

            # Try to match with existing templates
            matched = False
            for template in template_clusters.keys():
                similarity = self._calculate_similarity(processed, template)
                if similarity >= self.similarity_threshold:
                    template_clusters[template].append(log_msg)
                    matched = True
                    break

            # If no match, create new template
            if not matched:
                template_clusters[processed].append(log_msg)

        print(f"Identified {len(template_clusters)} different templates")

        # Select representative samples from each cluster
        selected_samples = []

        for template, logs in template_clusters.items():
            # Select first log in cluster as representative
            # Can be improved to select log closest to cluster center
            if len(logs) > 0:
                selected_samples.append(logs[0])

        # If too many samples, sort by cluster size and select top N
        if len(selected_samples) > self.max_samples:
            # Sort by cluster size
            template_sizes = [(template, len(logs)) for template, logs in template_clusters.items()]
            template_sizes.sort(key=lambda x: x[1], reverse=True)

            # Select top N templates
            top_templates = set([t[0] for t in template_sizes[:self.max_samples]])

            # Re-select samples
            selected_samples = []
            for template, logs in template_clusters.items():
                if template in top_templates:
                    selected_samples.append(logs[0])

        self.stats['unique_templates'] = len(template_clusters)

        return selected_samples

    def _hash_based_sampling(self, log_messages: List[str]) -> List[str]:
        """
        Hash-based sampling strategy

        Fast deduplication, selects samples from each hash bucket
        """
        print("\nUsing hash strategy for sampling...")

        # Hash buckets: {hash: [log list]}
        hash_buckets = defaultdict(list)

        for log_msg in log_messages:
            hash_value = self._get_log_hash(log_msg)
            hash_buckets[hash_value].append(log_msg)

        print(f"Identified {len(hash_buckets)} different hash categories")

        # Select first log from each hash bucket
        selected_samples = [logs[0] for logs in hash_buckets.values()]

        # If too many samples, random sampling
        if len(selected_samples) > self.max_samples:
            indices = np.random.choice(len(selected_samples), self.max_samples, replace=False)
            selected_samples = [selected_samples[i] for i in indices]

        self.stats['unique_templates'] = len(hash_buckets)

        return selected_samples

    def _embedding_based_sampling(self, log_messages: List[str]) -> List[str]:
        """
        Embedding-based sampling strategy (using sensitivesampling algorithm)

        Selects sample subset with maximum diversity
        """
        print("\nUsing Embedding + sensitivesampling strategy for sampling...")
        print("Note: This strategy requires pre-computed or real-time embedding calculation")

        # This is a simplified implementation
        # In actual use, can integrate sentence-transformers or OpenAI embedding

        # Temporarily use hash strategy as substitute
        print("Warning: Currently using hash strategy as substitute")
        return self._hash_based_sampling(log_messages)

    def _hybrid_sampling(self, log_messages: List[str]) -> List[str]:
        """
        Hybrid sampling strategy

        Combines advantages of BulkParse and hash methods
        """
        print("\nUsing hybrid strategy for sampling...")

        # Step 1: Use hash for fast deduplication
        hash_buckets = defaultdict(list)
        for log_msg in log_messages:
            hash_value = self._get_log_hash(log_msg)
            hash_buckets[hash_value].append(log_msg)

        # Step 2: Select one from each hash bucket
        hash_samples = [logs[0] for logs in hash_buckets.values()]

        # Step 3: Use BulkParse for further clustering
        selected_samples = self._drain_based_sampling(hash_samples)

        return selected_samples

    def _calculate_similarity(self, log1, log2):
        """Calculate similarity between two logs"""
        # Simple implementation: use token overlap
        tokens1 = set(log1.split())
        tokens2 = set(log2.split())

        if len(tokens1) == 0 or len(tokens2) == 0:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    def sample(self, log_messages: List[str]) -> List[str]:
        """
        Sample from log list

        Parameters:
        - log_messages: Original log list

        Returns: List of representative sampled logs
        """
        start_time = time.time()
        self.stats['total_logs'] = len(log_messages)

        print(f"\nStarting sampling: Total {len(log_messages)} logs")
        print(f"Sampling strategy: {self.sampling_strategy}")
        print(f"Target ratio: {self.sample_ratio * 100}%")
        print(f"Max samples: {self.max_samples}")

        # Select sampling method based on strategy
        if self.sampling_strategy == 'drain':
            selected = self._drain_based_sampling(log_messages)
        elif self.sampling_strategy == 'hash':
            selected = self._hash_based_sampling(log_messages)
        elif self.sampling_strategy == 'embedding':
            selected = self._embedding_based_sampling(log_messages)
        elif self.sampling_strategy == 'hybrid':
            selected = self._hybrid_sampling(log_messages)
        else:
            raise ValueError(f"Unsupported sampling strategy: {self.sampling_strategy}")

        # Update statistics
        self.stats['selected_samples'] = len(selected)
        self.stats['processing_time'] = time.time() - start_time

        print(f"\nSampling completed!")
        print(f"Original log count: {self.stats['total_logs']}")
        print(f"Identified templates: {self.stats['unique_templates']}")
        print(f"Selected samples: {self.stats['selected_samples']}")
        print(f"Sampling ratio: {self.stats['selected_samples'] / max(self.stats['total_logs'], 1) * 100:.2f}%")
        print(f"Processing time: {self.stats['processing_time']:.2f} seconds")

        return selected

    def sample_from_file(self, input_file: str, output_file: str = None) -> List[str]:
        """
        Read logs from file and sample

        Parameters:
        - input_file: Input log file path
        - output_file: Output file path (optional)

        Returns: List of sampled logs
        """
        print(f"\nReading log file: {input_file}")

        # Read log file
        log_messages = []
        try:
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        log_messages.append(line)
        except Exception as e:
            print(f"Failed to read file: {e}")
            return []

        print(f"Successfully read {len(log_messages)} logs")

        # Sample
        selected_samples = self.sample(log_messages)

        # Save results
        if output_file:
            self._save_samples(selected_samples, output_file)

        return selected_samples

    def _save_samples(self, samples: List[str], output_file: str):
        """Save sampling results to file"""
        # Save as plain text format (one log per line)
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in samples:
                f.write(sample + '\n')

        print(f"\nSamples saved to: {output_file}")

        # Also save as CSV format (with statistics)
        csv_file = output_file.rsplit('.', 1)[0] + '.csv'
        df = pd.DataFrame({
            'log': samples,
            'index': range(len(samples))
        })
        df.to_csv(csv_file, index=False)
        print(f"CSV format saved to: {csv_file}")

    def generate_initial_template_library(self, samples: List[str], output_path: str):
        """
        Generate initial template library based on sampling results

        Parameters:
        - samples: Sampled log samples
        - output_path: Output template library file path
        """
        print(f"\nGenerating initial template library...")

        # Use BulkParse strategy to extract templates
        template_data = []

        for sample in samples:
            content = self._extract_content(sample)
            template = self._preprocess_log(content)

            template_data.append({
                'log': sample,
                'template': template
            })

        # Save as CSV format
        df = pd.DataFrame(template_data)
        df.to_csv(output_path, index=False)

        print(f"Initial template library saved to: {output_path}")
        print(f"Total {len(template_data)} templates")

    def print_stats(self):
        """Print statistics"""
        print("\n" + "="*60)
        print("Sampling Statistics")
        print("="*60)
        print(f"Total logs: {self.stats['total_logs']}")
        print(f"Unique templates: {self.stats['unique_templates']}")
        print(f"Selected samples: {self.stats['selected_samples']}")
        print(f"Sampling ratio: {self.stats['selected_samples'] / max(self.stats['total_logs'], 1) * 100:.2f}%")
        print(f"Processing time: {self.stats['processing_time']:.2f} seconds")
        print("="*60 + "\n")


# ============ Usage Examples ============

def example_usage():
    """Usage example"""

    print("="*70)
    print("Sensitive Log Sampler - Usage Example")
    print("="*70)

    # Configure parameters
    regex_patterns = [
        r'blk_(|-)[0-9]+',  # block id
        r'(/|)([0-9]+\.){3}[0-9]+(:[0-9]+|)(:|)',  # IP
        r'(?<=[^A-Za-z0-9])(\-?\+?\d+)(?=[^A-Za-z0-9])|[0-9]+$',  # Numbers
    ]

    # Create sampler
    sampler = SensitiveLogSampler(
        sampling_strategy='hybrid',  # Use hybrid strategy
        sample_ratio=0.1,  # Sample 10%
        max_samples=1000,  # Maximum 1000 samples
        regex=regex_patterns,
        similarity_threshold=0.5
    )

    # Simulate log data (in actual use, read from file)
    print("\nGenerating simulated log data...")
    mock_logs = [
        "PacketResponder 1 for block blk_38865049064139660 terminating",
        "PacketResponder 0 for block blk_-6952295868487656571 terminating",
        "PacketResponder 2 for block blk_8229193803249955061 terminating",
        "BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.73.220:50010 is added to blk_7128370237687728475 size 67108864",
        "BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.43.115:50010 is added to blk_3050920587428079149 size 67108864",
        "Received block blk_3587508140051953248 of size 67108864 from /10.251.42.84",
        "Received block blk_5402003568334525940 of size 67108864 from /10.251.214.112",
        "Receiving block blk_5792489080791696128 src: /10.251.30.6:33145 dest: /10.251.30.6:50010",
        "Receiving block blk_1724757848743533110 src: /10.251.111.130:49851 dest: /10.251.111.130:50010",
    ]

    # Repeat to generate more logs to simulate large-scale data
    print("Generating 100k simulated logs...")
    mock_logs_large = []
    for i in range(100000):
        mock_logs_large.append(mock_logs[i % len(mock_logs)])

    # Perform sampling
    sampled_logs = sampler.sample(mock_logs_large)

    # Print statistics
    sampler.print_stats()

    # Print sampling results
    print("\nSampling results (first 10):")
    print("-"*70)
    for i, log in enumerate(sampled_logs[:10], 1):
        print(f"{i}. {log}")

    print(f"\n... Total {len(sampled_logs)} samples")


def example_with_file():
    """Example reading from file"""

    print("\n" + "="*70)
    print("Sampling from log file")
    print("="*70)

    # Configure parameters
    regex_patterns = [
        r'blk_(|-)[0-9]+',
        r'(/|)([0-9]+\.){3}[0-9]+(:[0-9]+|)(:|)',
        r'(?<=[^A-Za-z0-9])(\-?\+?\d+)(?=[^A-Za-z0-9])|[0-9]+$',
    ]

    # Create sampler
    sampler = SensitiveLogSampler(
        sampling_strategy='hybrid',
        sample_ratio=0.05,  # Sample 5%
        max_samples=500,
        regex=regex_patterns,
        similarity_threshold=0.5
    )

    # Sample from file
    input_file = '../../data/loghub_2k/HDFS/HDFS_2k.log'
    output_file = 'sampled_logs_HDFS.txt'

    print(f"\nInput file: {input_file}")
    print(f"Output file: {output_file}")

    # Note: Actual file path required here
    # sampled_logs = sampler.sample_from_file(input_file, output_file)

    # Generate initial template library
    # sampler.generate_initial_template_library(sampled_logs, 'initial_template_library.csv')

    print("\nPlease adjust file paths according to actual situation")


if __name__ == '__main__':
    # Run example
    example_usage()

