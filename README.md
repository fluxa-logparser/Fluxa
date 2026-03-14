<<<<<<< HEAD
# Fluxa: log parsing system combining BulkParse and DeepParse with automatic routing and template learning
=======

# Fluxa: A Hybrid LLM-Agent Framework for Adaptive Log Parsing


A hybrid log parsing system combining **BulkParse** (fast rule-based parsing) and **DeepParse** (LLM-based parsing) with intelligent routing and template learning capabilities.

## Features

- **BulkParse**: Fast, rule-based log parser using Drain algorithm
- **DeepParse**: LLM-based parser using OpenAI GPT models for learning new log patterns
- **LogRouter**: Intelligent routing system that automatically selects between BulkParse and DeepParse
- **Template Learning**: Automatically learns and stores templates for fast parsing
- **Sensitive Sampling**: Diversity-aware sampling algorithm for representative log selection
- **Multi-Dataset Support**: Supports 16 benchmark log datasets

## Installation

### Requirements

```bash
pip install -r requirements.txt
```

### Dependencies

- Python 3.8+
- pandas
- numpy
- scikit-learn
- openai
- tqdm
- tiktoken

## Usage

### 1. Quick Start with LogRouter (Recommended)

```python
from logparser import LogRouter

# Initialize LogRouter
router = LogRouter(
    sampler_config={'strategy': 'hybrid', 'max_samples': 1000},
    drain_config={'similarity_threshold': 0.5},
    working_dir='./log_router_data'
)

# Parse logs
log_file = 'path/to/your/logfile.log'
results = router.parse_file(log_file, batch_size=100)

# Results contain: {'log': str, 'template': str, 'parser': str}
```

### 2. Run Full Benchmark on All 16 Datasets

```bash
cd logparser
python main.py
```

This will:
- Parse all 16 datasets in `data/loghub_2k/`
- Generate templates and structured outputs
- Calculate accuracy metrics (PA, PTA, RTA, GA)
- Save results to `outputs/DeepParse_bechmark_result.csv`

### 3. Use BulkParse Only

```python
from logparser.BulkParse import BulkParse

parser = Bulk.Parse(
    log_format='<Date> <Time> <Pid> <Level> <Component>: <Content>',
    regex=[],  # regex patterns for variable extraction
    st=0.5  # similarity threshold
)

parser.parse('path/to/logfile.log')
```

### 4. Use DeepParse Only

First, generate embeddings (one-time setup):

```bash
cd logparser/DeepParse
python embedding.py -key YOUR_OPENAI_API_KEY
```

Then run parsing:

```bash
python demo.py -key YOUR_OPENAI_API_KEY --dataset HDFS --limit 2000
```

## Fluxa Versions

This project supports two versions of Fluxa:

### 1. Fluxa (Prompt Version)

The Prompt version uses OpenAI's GPT models with carefully designed prompts for log parsing. This is the default configuration described in the Usage section above.

**Setup:**
```bash
pip install openai
```

**Configuration:**
```python
import openai
openai.api_key = "your-api-key-here"
```

### 2. Fluxa (Fine-tuned Version)

The Fine-tuned version uses a specially fine-tuned Llama model (Meta-Llama-3.1-13B-Fluxa) optimized for log parsing tasks. This version provides better performance and doesn't require OpenAI API keys.

**Installation:**
```bash
pip install llama-cpp-python
```

**Usage:**
```python
from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id="Fluxa-logparser/fluxa",
    filename="Meta-Llama-3.1-13B-Fluxa.gguf",
)
```
### 3. Fluxa (LoRA Adapter Version)

The LoRA Adapter version uses a parameter-efficient fine-tuned adapter for the Llama model.  
Instead of downloading the full fine-tuned model, this version loads a lightweight LoRA adapter
(`adapter_model.safetensors` + `adapter_config.json`) on top of the base model.

This significantly reduces the model size and makes deployment easier.

---

#### Requirements

```bash
pip install transformers peft accelerate

## API Configuration

### For Fluxa (Prompt Version)

**Method 1: Command Line Argument**
```bash
python demo.py -key sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

**Method 2: Environment Variable**
```bash
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
python demo.py
```

**Method 3: In Code**
```python
import openai
openai.api_key = "your-api-key-here"
```

### For Fluxa (Fine-tuned Version)

The fine-tuned version uses llama-cpp-python and automatically downloads the model from Hugging Face on first use. No additional configuration needed.

## Project Structure

```
logparser-main/
├── logparser/
│   ├── BulkParse/          # Fast rule-based parser
│   │   ├── BulkParse.py
│   │   ├── benchmark.py
│   │   └── demo.py
│   ├── DeepParse/          # LLM-based parser
│   │   ├── DeepParse.py
│   │   ├── demo.py
│   │   ├── embedding.py
│   │   └── benchmark.py
│   ├── utils/              # Utility functions
│   │   ├── evaluator.py    # Accuracy metrics
│   │   └── logloader.py    # Log data loading
│   ├── log_route.py        # LogRouter implementation
│   ├── sensitive_sampler.py # Diversity sampling
│   └── main.py            # Main benchmark script
├── data/
│   └── loghub_2k/         # 16 benchmark datasets
├── docs/                  # Documentation
├── example/               # Usage examples
└── requirements.txt
```

## Datasets

Supports 14 benchmark datasets:
- Android, Apache, BGL, Hadoop, HDFS, HealthApp, HPC, Linux, Mac, OpenSSH, OpenStack, Proxifier, Spark, Thunderbird, Windows, Zookeeper

## Accuracy Metrics

The system evaluates parsing quality using four metrics:

- **PA (Parsing Accuracy)**: Correct templates / Total logs
- **GA (Grouping Accuracy)**: Correctly grouped logs / Total logs

## Output Files

Running `main.py` generates:

```
outputs/
├── DeepParse_bechmark_result.csv  # Summary metrics for all datasets
└── DeepParse_results/
    ├── {dataset}_2k.log_structured.csv  # Parsed logs with templates
    ├── {dataset}_2k.log_templates.csv   # Unique templates
    ├── {dataset}_results.csv            # Detailed parsing results
    └── {dataset}_router/                # Learned template library
        ├── template_library.csv
        └── router_stats.json
```

## Key Features Explained

### LogRouter

The LogRouter intelligently routes logs to either:
- **BulkParse**: For known patterns (fast, ~0.0002s per log)
- **DeepParse**: For new/unknown patterns (slower, but learns templates)

It automatically:
- Maintains a template library
- Learns new templates from DeepParse results
- Routes similar logs to BulkParse for speed

### Sensitive Sampling

The `sensitive_sampler.py` implements diversity-aware sampling:

- **drain**: BulkParse-based clustering sampling
- **hash**: Fast deduplication via hashing
- **embedding**: DPP-based diversity sampling (requires embeddings)
- **hybrid**: Combines hash + drain (recommended)

## Troubleshooting

### Issue: "Embedding path does not exist"

**Solution**: Run `embedding.py` first to generate embeddings
```bash
cd logparser/DeepParse
python embedding.py -key YOUR_API_KEY
```
