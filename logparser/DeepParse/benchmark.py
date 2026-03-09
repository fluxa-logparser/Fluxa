import os
import pandas as pd
import argparse

parser = argparse.ArgumentParser(description="Runs batchtest.py with a provided OpenAI key.")
parser.add_argument('-key', type=str, default=None, help='OpenAI API key (or set OPENAI_API_KEY environment variable)')
args = parser.parse_args()

# Get API key from argument or environment variable
api_key = args.key or os.environ.get('OPENAI_API_KEY')

if not api_key:
    print("Error: Please provide OpenAI API key via -key argument or OPENAI_API_KEY environment variable")
    print("Example: python benchmark.py -key sk-your-api-key-here")
    print("Or: export OPENAI_API_KEY='sk-your-api-key-here'")
    exit(1)

datasets = ["HDFS", "Spark", "BGL", "Windows", "Linux", "Android", "Mac", "Hadoop", "HealthApp", "OpenSSH", "Thunderbird", "Proxifier", "Apache", "HPC", "Zookeeper", "OpenStack"]
    
for dataset in datasets:
    os.system(f"python demo.py -key {api_key} --dataset {dataset} --evaluate True")
df_results = pd.read_csv("DeepParse_bechmark_result.csv")
print(df_results)