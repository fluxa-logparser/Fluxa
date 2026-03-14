<<<<<<< HEAD
# Fluxa: A Hybrid LLM-Agent Framework for Adaptive Log Parsing
=======


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

### 2. Fluxa (LoRA Adapter Version)

The LoRA Adapter version uses a LoRA (Low-Rank Adaptation) adapter fine-tuned for log parsing tasks. This version provides better performance and doesn't require OpenAI API keys.

**Download from Hugging Face:**
Visit: https://huggingface.co/Fluxa-logparser/fluxa/tree/main

**Installation:**
```bash
pip install transformers
pip install peft
pip install torch
pip install accelerate
```

**Configuration:**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel, PeftConfig

# Load base model
model_name = "meta-llama/Llama-3.1-13b"  # or your preferred base model
tokenizer = AutoTokenizer.from_pretrained(model_name)
base_model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)

# Load LoRA adapter
model_path = "Fluxa-logparser/fluxa"  # Downloaded from Hugging Face
model = PeftModel.from_pretrained(base_model, model_path)

# Use for inference
def parse_log(log_message):
    prompt = f"Parse this log message: {log_message}"
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=256)
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return result
```

**Alternative: Using with Pipeline**
```python
from transformers import pipeline

# Load model with LoRA adapter
pipe = pipeline(
    "text-generation",
    model="Fluxa-logparser/fluxa",
    tokenizer=model_name,
    device_map="auto"
)

# Parse logs
result = pipe("Parse this log: <your log message>")

```
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

### For Fluxa (LoRA Adapter Version)

**Step 1: Download LoRA Adapter**
```bash
# Using git clone
git clone https://huggingface.co/Fluxa-logparser/fluxa

# Or download manually from:
# https://huggingface.co/Fluxa-logparser/fluxa/tree/main
```

**Step 2: Model Configuration**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

# Configuration
config = {
    "base_model": "meta-llama/Llama-2-7b-hf",  # Base model
    "adapter_path": "./fluxa",                   # Path to downloaded adapter
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "max_length": 512,
    "temperature": 0.1
}

# Load model
tokenizer = AutoTokenizer.from_pretrained(config["base_model"])
base_model = AutoModelForCausalLM.from_pretrained(
    config["base_model"],
    torch_dtype=torch.float16 if config["device"] == "cuda" else torch.float32,
    device_map="auto"
)

# Load LoRA adapter
model = PeftModel.from_pretrained(base_model, config["adapter_path"])
model = model.merge_and_unload()  # Merge adapter for faster inference
```

**Step 3: Run Inference**
```python
def parse_logs(log_messages):
    """Parse log messages using Fluxa LoRA adapter"""
    results = []
    for log_msg in log_messages:
        prompt = f"Parse the following log message:\n{log_msg}\n\nParsed output:"
        inputs = tokenizer(prompt, return_tensors="pt").to(config["device"])
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=config["temperature"],
            do_sample=True
        )
        parsed = tokenizer.decode(outputs[0], skip_special_tokens=True)
        results.append(parsed)
    return results
```

**Recommended Settings:**
- GPU: NVIDIA GPU with 8GB+ VRAM (use CPU with quantization for lower memory)
- Base Model: Llama-2-7b-hf or Meta-Llama-3.1-8B
- Adapter: Fluxa-logparser/fluxa (from Hugging Face)
- Batch Size: 1 for inference, adjust based on GPU memory

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
