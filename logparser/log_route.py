#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import re
import pandas as pd
import json
import time
from typing import List, Dict, Optional
from collections import defaultdict
from difflib import SequenceMatcher

# Import sampler
from sensitive_sampler import SensitiveLogSampler


class LogRouter:
    """
    Intelligent Log Router (Integrated Version)

    Integrates sampling, parsing, and routing functionality
    """

    def __init__(self,
                 sampler_config: Dict = None,
                 drain_config: Dict = None,
                 deepParse_api_key: str = None,
                 working_dir: str = './log_router_data',
                 auto_load_templates: bool = True):
        """
        Initialize log router

        Parameters:
        - sampler_config: Sampler configuration
        - drain_config: BulkParse parser configuration
        - deepParse_api_key: DeepParse/OpenAI API key
        - working_dir: Working directory (saves template library and intermediate files)
        - auto_load_templates: Whether to auto-load existing template library (default True)
        """
        self.working_dir = working_dir
        self.deepParse_api_key = deepParse_api_key
        self.auto_load_templates = auto_load_templates

        # Create working directory
        os.makedirs(working_dir, exist_ok=True)

        # Default configuration
        self.sampler_config = sampler_config or {
            'sampling_strategy': 'hybrid',
            'sample_ratio': 0.05,
            'max_samples': 500,
            'similarity_threshold': 0.5,
            'regex': [
                r'blk_(|-)[0-9]+',
                r'(/|)([0-9]+\.){3}[0-9]+(:[0-9]+|)(:|)',
                r'(?<=[^A-Za-z0-9])(\-?\+?\d+)(?=[^A-Za-z0-9])|[0-9]+$',
            ]
        }

        self.drain_config = drain_config or {
            'similarity_threshold': 0.5,
            'regex': [
                r'blk_(|-)[0-9]+',
                r'(/|)([0-9]+\.){3}[0-9]+(:[0-9]+|)(:|)',
                r'(?<=[^A-Za-z0-9])(\-?\+?\d+)(?=[^A-Za-z0-9])|[0-9]+$',
            ]
        }

        # Initialize components (lazy initialization)
        self.sampler = None
        self.initialized = False

        # Template library
        self.template_library = {}
        self.template_index = defaultdict(list)

        # Statistics
        self.stats = {
            'total_logs_processed': 0,
            'logs_by_drain': 0,
            'logs_by_deepParse': 0,
            'new_templates_learned': 0,
            'initialization_time': 0,
            'processing_time': 0
        }

        # Template library paths
        self.template_library_path = os.path.join(working_dir, 'template_library.csv')
        self.sampled_logs_path = os.path.join(working_dir, 'sampled_logs.txt')
        self.stats_path = os.path.join(working_dir, 'router_stats.json')

        # Auto-load existing template library (silent mode)
        if self.auto_load_templates and os.path.exists(self.template_library_path):
            self._load_template_library(verbose=False)
            # Also load statistics
            if os.path.exists(self.stats_path):
                self.load_state(verbose=False)

    # ==================== Initialization Phase ====================

    def initialize_from_file(self, initial_log_file: str, force_reinit: bool = False):
        """
        Initialize router from historical log file

        Parameters:
        - initial_log_file: Initial log file path
        - force_reinit: Whether to force re-initialization

        Process:
        1. Use Sensitive Sampler to sample representative logs
        2. Use rules to generate initial templates (or call DeepParse)
        3. Generate initial template library
        """
        print("\n" + "="*70)
        print("Log Router Initialization Phase")
        print("="*70)

        # Check if already initialized
        if os.path.exists(self.template_library_path) and not force_reinit:
            print(f"\nTemplate library already exists: {self.template_library_path}")
            print("To re-initialize, please set force_reinit=True")

            self._load_template_library()
            self.initialized = True
            return

        start_time = time.time()

        # Step 1: Create sampler
        print("\n[Step 1/3] Creating sensitive sampler...")
        self.sampler = SensitiveLogSampler(**self.sampler_config)
        print(f"[OK] Sampler configuration: {self.sampler_config['sampling_strategy']} strategy")
        print(f"[OK] Target sample count: {self.sampler_config['max_samples']}")

        # Step 2: Sample
        print(f"\n[Step 2/3] Sampling from historical logs...")
        print(f"Input file: {initial_log_file}")

        sampled_logs = self.sampler.sample_from_file(
            initial_log_file,
            self.sampled_logs_path
        )

        print(f"\n[OK] Sampling completed: {len(sampled_logs)} representative logs")
        print(f"[OK] Identified templates: {self.sampler.stats['unique_templates']}")
        print(f"[OK] Sampling results saved: {self.sampled_logs_path}")

        # Step 3: Generate initial template library
        print(f"\n[Step 3/3] Generating initial template library...")
        print("Processing sampled logs...")

        # Use sampler's template generation function
        self.sampler.generate_initial_template_library(
            sampled_logs,
            self.template_library_path
        )

        print(f"[OK] Initial template library generated: {self.template_library_path}")

        # Load template library into memory
        self._load_template_library()

        # Update statistics
        self.stats['initialization_time'] = time.time() - start_time
        self.initialized = True

        print("\n" + "="*70)
        print("Initialization Completed!")
        print("="*70)
        print(f"Initialization time: {self.stats['initialization_time']:.2f} seconds")
        print(f"Template library path: {self.template_library_path}")
        print(f"Template count: {len(self.template_library)}")
        print("="*70)

    def initialize_from_logs(self, log_messages: List[str], force_reinit: bool = False):
        """Initialize router from log list"""
        print("\n" + "="*70)
        print("Log Router Initialization Phase (from log list)")
        print("="*70)

        if os.path.exists(self.template_library_path) and not force_reinit:
            print(f"\nTemplate library already exists: {self.template_library_path}")
            self._load_template_library()
            self.initialized = True
            return

        start_time = time.time()

        # Create sampler
        print("\n[Step 1/3] Creating sensitive sampler...")
        self.sampler = SensitiveLogSampler(**self.sampler_config)

        # Sample
        print(f"\n[Step 2/3] Sampling logs...")
        sampled_logs = self.sampler.sample(log_messages)
        print(f"[OK] Sampling completed: {len(sampled_logs)} representative logs")

        # Generate template library
        print(f"\n[Step 3/3] Generating template library...")
        self.sampler.generate_initial_template_library(
            sampled_logs,
            self.template_library_path
        )

        # Load template library
        self._load_template_library()

        self.stats['initialization_time'] = time.time() - start_time
        self.initialized = True

        print("\n[OK] Initialization completed!")

    # ==================== Template Library Management ====================

    def _load_template_library(self, verbose: bool = True):
        """
        Load template library into memory

        Parameters:
        - verbose: Whether to print detailed information
        """
        if verbose:
            print("\nLoading template library...")

        if not os.path.exists(self.template_library_path):
            if verbose:
                print(f"Warning: Template library file does not exist: {self.template_library_path}")
            return

        df = pd.read_csv(self.template_library_path)

        # Build template dictionary
        self.template_library = {}
        for _, row in df.iterrows():
            original_log = row['log']
            template = row['template']
            self.template_library[original_log] = template

        # Build index
        self._build_template_index()

        if verbose:
            print(f"[OK] Template library loaded, total {len(self.template_library)} templates")

    def _build_template_index(self):
        """Build template index to accelerate lookup"""
        self.template_index = defaultdict(list)

        for template in self.template_library.values():
            keywords = self._extract_keywords(template)
            template_length = len(template.split())

            if keywords:
                first_keyword = keywords[0]
                self.template_index[first_keyword].append({
                    'template': template,
                    'length': template_length,
                    'keywords': keywords
                })

    def _extract_keywords(self, template):
        """Extract keywords from template"""
        cleaned = template.replace('<*>', ' ')
        keywords = [word for word in cleaned.split() if word.strip()]
        return keywords

    def _add_template_to_library(self, log_message, template):
        """Add new template to template library"""
        self.template_library[log_message] = template

        # Update index
        keywords = self._extract_keywords(template)
        if keywords:
            first_keyword = keywords[0]
            self.template_index[first_keyword].append({
                'template': template,
                'length': len(template.split()),
                'keywords': keywords
            })

    # ==================== Log Parsing (BulkParse + DeepParse) ====================

    def _preprocess_log(self, log_message):
        """Preprocess log"""
        processed = log_message
        for regex_pattern in self.drain_config.get('regex', []):
            processed = re.sub(regex_pattern, '<*>', processed)
        return processed

    def _match_template_with_drain(self, log_message):
        """
        Match template using BulkParse method

        Returns: (matched, template)
        - matched: Whether match succeeded
        - template: Matched template
        """
        # Preprocess
        processed_log = self._preprocess_log(log_message)

        # Extract keywords
        log_keywords = self._extract_keywords(processed_log)

        if not log_keywords:
            return False, None

        # Search in index
        first_keyword = log_keywords[0]

        if first_keyword not in self.template_index:
            return False, None

        # Calculate similarity
        best_match = None
        best_similarity = 0

        for candidate in self.template_index[first_keyword]:
            similarity = self._calculate_similarity(
                processed_log,
                candidate['template'],
                log_keywords,
                candidate['keywords']
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = candidate['template']

        # Check if exceeds threshold
        threshold = self.drain_config.get('similarity_threshold', 0.5)
        if best_similarity >= threshold:
            return True, best_match

        return False, None

    def _calculate_similarity(self, log, template, log_keywords, template_keywords):
        """Calculate similarity between log and template"""
        # Sequence similarity
        sequence_sim = SequenceMatcher(None, log, template).ratio()

        # Keyword overlap
        log_keywords_set = set(log_keywords)
        template_keywords_set = set(template_keywords)

        if len(template_keywords_set) > 0:
            keyword_overlap = len(log_keywords_set & template_keywords_set) / len(template_keywords_set)
        else:
            keyword_overlap = 0

        # Length similarity
        log_length = len(log.split())
        template_length = len(template.split())
        length_sim = 1 - abs(log_length - template_length) / max(log_length, template_length)

        # Overall similarity
        similarity = (sequence_sim * 0.5 + keyword_overlap * 0.3 + length_sim * 0.2)

        return similarity

    def _parse_with_drain(self, log_message, template):
        """Parse log using BulkParse method"""
        return {
            'log': log_message,
            'template': template,
            'method': 'BulkParse',
            'matched': True
        }

    def _parse_with_deepParse(self, log_message):
        """Parse log using DeepParse method (when matching fails)"""
        # Simplified implementation: generate template based on rules
        template = self._generate_fallback_template(log_message)

        return {
            'log': log_message,
            'template': template,
            'method': 'DeepParse',
            'matched': False
        }

    def _generate_fallback_template(self, log_message):
        """Generate fallback template"""
        template = log_message

        # Replace numbers
        template = re.sub(r'\b\d+\b', '<*>', template)

        # Replace IP addresses
        template = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<*>', template)

        # Replace block IDs
        template = re.sub(r'blk_[-]?\d+', 'blk_<*>', template)

        return template

    # ==================== Routing Logic ====================

    def route_and_parse(self, log_message: str) -> Dict:
        """
        Route and parse single log

        Core logic:
        1. First use BulkParse to match template library
        2. Match succeeded → Return BulkParse result
        3. Match failed → Use DeepParse to parse → Update template library

        Parameters:
        - log_message: Log message

        Returns: Parsing result dictionary
        """
        # Check initialization status
        if not self.initialized:
            raise RuntimeError("Log Router not initialized! Please call initialize_from_file() or initialize_from_logs() first")

        start_time = time.time()

        # Step 1: Try to match with BulkParse
        matched, template = self._match_template_with_drain(log_message)

        if matched:
            # Step 2a: BulkParse match succeeded
            result = self._parse_with_drain(log_message, template)
            self.stats['logs_by_drain'] += 1
        else:
            # Step 2b: BulkParse match failed, use DeepParse
            result = self._parse_with_deepParse(log_message)
            self.stats['logs_by_deepParse'] += 1

            # Learn new template
            if not result.get('matched', False):
                self._add_template_to_library(log_message, result['template'])
                self.stats['new_templates_learned'] += 1

        # Update statistics
        self.stats['total_logs_processed'] += 1
        self.stats['processing_time'] += time.time() - start_time

        return result

    def route_and_parse_batch(self, log_messages: List[str]) -> List[Dict]:
        """Batch route and parse logs"""
        print(f"\nProcessing {len(log_messages)} logs...")

        results = []
        new_templates = []

        for i, log_msg in enumerate(log_messages):
            try:
                result = self.route_and_parse(log_msg)
                results.append(result)

                # Record new templates
                if not result.get('matched', False):
                    new_templates.append({
                        'log': log_msg,
                        'template': result['template']
                    })

                # Progress display
                if (i + 1) % 100 == 0:
                    print(f"  Processed: {i + 1}/{len(log_messages)}")

            except Exception as e:
                print(f"Processing failed (log {i}): {e}")
                results.append({
                    'log': log_msg,
                    'error': str(e),
                    'method': 'Error'
                })

        # If there are new templates, batch save
        if new_templates:
            print(f"\nLearned {len(new_templates)} new templates, updating template library...")
            self._save_updated_library()

        return results

    def parse_file(self, input_file: str, output_file: str = None):
        """Parse log file"""
        print(f"\nReading log file: {input_file}")

        # Read logs
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            log_messages = [line.strip() for line in f if line.strip()]

        print(f"Read {len(log_messages)} logs")

        # Batch process
        results = self.route_and_parse_batch(log_messages)

        # Save results
        if output_file:
            self._save_results(results, output_file)

        # Print statistics
        self.print_stats()

        return results

    def _save_updated_library(self):
        """Save updated template library"""
        df_data = []

        for log, template in self.template_library.items():
            df_data.append({
                'log': log,
                'template': template
            })

        df = pd.DataFrame(df_data)
        df.to_csv(self.template_library_path, index=False)

        print(f"[OK] Template library updated: {self.template_library_path}")

    def _save_results(self, results: List[Dict], output_file: str):
        """Save parsing results"""
        df_data = []

        for result in results:
            if 'error' in result:
                df_data.append({
                    'log': result['log'],
                    'template': 'ERROR',
                    'method': result['method'],
                    'error': result['error']
                })
            else:
                df_data.append({
                    'log': result['log'],
                    'template': result['template'],
                    'method': result['method'],
                    'matched': result.get('matched', False)
                })

        df = pd.DataFrame(df_data)
        df.to_csv(output_file, index=False)
        print(f"\nResults saved to: {output_file}")

    def print_stats(self):
        """Print statistics"""
        total = self.stats['total_logs_processed']

        print("\n" + "="*70)
        print("Log Router Statistics")
        print("="*70)
        print(f"Initialization status: {'[OK] Initialized' if self.initialized else '[X] Not initialized'}")
        print(f"Initialization time: {self.stats['initialization_time']:.2f} seconds")
        print(f"\nProcessing statistics:")
        print(f"  Total logs: {total}")
        print(f"  BulkParse parsed: {self.stats['logs_by_drain']} ({self.stats['logs_by_drain']/max(total,1)*100:.1f}%)")
        print(f"  DeepParse parsed: {self.stats['logs_by_deepParse']} ({self.stats['logs_by_deepParse']/max(total,1)*100:.1f}%)")
        print(f"  New templates learned: {self.stats['new_templates_learned']}")
        print(f"  Total processing time: {self.stats['processing_time']:.2f} seconds")
        if total > 0:
            print(f"  Average speed: {self.stats['processing_time']/total:.4f} seconds/log")
        print("="*70 + "\n")

    def save_state(self):
        """Save router state"""
        state = {
            'stats': self.stats,
            'initialized': self.initialized,
            'sampler_config': self.sampler_config,
            'drain_config': self.drain_config,
        }

        with open(self.stats_path, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"State saved to: {self.stats_path}")

    def load_state(self, verbose: bool = True):
        """
        Load router state

        Parameters:
        - verbose: Whether to print detailed information
        """
        if os.path.exists(self.stats_path):
            with open(self.stats_path, 'r') as f:
                state = json.load(f)

            self.stats = state.get('stats', self.stats)
            self.initialized = state.get('initialized', False)

            if verbose:
                print(f"State loaded: {self.stats_path}")

            if self.initialized:
                self._load_template_library(verbose=verbose)

            return True
        return False


# ============ Usage Examples ============

def example_usage():
    """Usage example"""

    print("="*70)
    print("Log Router Usage Example")
    print("="*70)

    # Create router
    router = LogRouter(
        sampler_config={
            'sampling_strategy': 'hybrid',
            'sample_ratio': 0.05,
            'max_samples': 100,
        },
        drain_config={
            'similarity_threshold': 0.5,
        },
        working_dir='./demo_output'
    )

    # Simulate data
    historical_logs = [
        "PacketResponder 1 for block blk_38865049064139660 terminating",
        "BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.73.220:50010 is added to blk_7128370237687728475 size 67108864",
        "Received block blk_3587508140051953248 of size 67108864 from /10.251.42.84",
    ]

    # Generate more data
    for i in range(1000):
        base = historical_logs[i % len(historical_logs)]
        historical_logs.append(base.replace('blk_', f'blk_{i}_'))

    # Initialize
    print("\nPhase 1: Initialization")
    router.initialize_from_logs(historical_logs, force_reinit=True)

    # Parse new logs
    print("\nPhase 2: Parse new logs")
    new_logs = [
        # Seen templates (should use BulkParse)
        "PacketResponder 5 for block blk_999888777 terminating",

        # New templates (should use DeepParse)
        "Error connecting to database server 192.168.1.100 port 3306",
    ]

    results = router.route_and_parse_batch(new_logs)

    # Print results
    print("\nParsing results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['log'][:60]}...")
        print(f"   Template: {result['template'][:60]}...")
        print(f"   Method: {result['method']}")
        print(f"   Matched: {'Yes' if result.get('matched') else 'No (New learning)'}")

    # Print statistics
    router.print_stats()

    print("\nExample completed!")


if __name__ == '__main__':
    example_usage()

    print("\n" + "="*70)
    print("Usage Instructions")
    print("="*70)
    print("""
New version of Log Router (Integrated Version):

1. Initialization:
   router = LogRouter(working_dir='./my_router')
   router.initialize_from_file('historical_logs.log')

2. Parse:
   result = router.route_and_parse("log message")

3. Batch parse:
   results = router.route_and_parse_batch(log_list)

4. Parse file:
   results = router.parse_file('input.log', 'output.csv')

5. View statistics:
   router.print_stats()

Core improvements:
- Integrated all features of hybrid_parser
- New logs first use BulkParse matching, fallback to DeepParse on failure
- Auto-update template library
- No separate hybrid_parser file needed
    """)
