import pyarrow.parquet as pq
import json

def parquet_to_jsonl(parquet_file, jsonl_file):
    # Read the Parquet file
    table = pq.read_table(parquet_file)
    
    # Open the output JSONL file
    with open(jsonl_file, 'w') as f:
        # Iterate through rows and write as JSON lines
        for row in table.to_pylist():
            json.dump(row, f)
            f.write('\n')

# Usage
parquet_to_jsonl('/Users/mihirchintawar/agent/test-00000-of-00001 (1).parquet', 'SWE-bench_Lite-test.jsonl')