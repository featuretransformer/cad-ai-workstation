import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from datasets.registry import get_available_adapters
from retrieval.index import KnowledgeIndex

def main():
    print("Initializing KnowledgeIndex...")
    index = KnowledgeIndex()
    
    print("Checking available dataset adapters...")
    # The registry uses settings.datasets_dir which we need to make sure points to ../datasets
    # In config.py it's probably looking at DATASETS_DIR env var or defaults to ../datasets
    adapters = get_available_adapters()
    
    if not adapters:
        print("No adapters or dataset files found!")
        sys.exit(1)
        
    print(f"Found {len(adapters)} available datasets: {list(adapters.keys())}")
    
    total_indexed = 0
    for name, adapter in adapters.items():
        print(f"Processing dataset: {name}")
        batch_size = 1000
        dataset_indexed = 0
        records_to_index = []
        for record in adapter.iterate_records(limit=None):
            try:
                doc = adapter.to_cadir(record)
                records_to_index.append((doc, name, None))
            except Exception as e:
                # Don't print every error to avoid spamming the console on massive datasets
                pass
            
            if len(records_to_index) >= batch_size:
                try:
                    count = index.bulk_index_documents(records_to_index)
                    dataset_indexed += count
                    total_indexed += count
                    records_to_index = []
                    print(f"  Indexed {dataset_indexed} items so far for {name}...")
                except Exception as e:
                    print(f"  Error indexing batch for {name}: {e}")
                    records_to_index = []
        
        if records_to_index:
            try:
                count = index.bulk_index_documents(records_to_index)
                dataset_indexed += count
                total_indexed += count
                print(f"  Successfully indexed {dataset_indexed} total items for {name}")
            except Exception as e:
                print(f"  Error indexing final batch for {name}: {e}")
        elif dataset_indexed == 0:
            print(f"  No valid records to index for {name}")

    print(f"Finished! Total documents indexed: {total_indexed}")
    print(f"Database now contains {index.get_document_count()} items.")

if __name__ == "__main__":
    main()
