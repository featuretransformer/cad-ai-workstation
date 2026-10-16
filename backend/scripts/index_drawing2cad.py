import sys
import time
sys.path.insert(0, '.')
from datasets.registry import _ADAPTER_REGISTRY
from retrieval.index import KnowledgeIndex

def main():
    print("Initializing KnowledgeIndex...")
    index = KnowledgeIndex()
    with index._get_connection() as conn:
        db_ids = set(r[0] for r in conn.execute('SELECT id FROM cad_examples').fetchall())
    print(f"Existing records in DB: {len(db_ids)}")
    
    adapter_cls = _ADAPTER_REGISTRY['drawing2cad']
    adapter = adapter_cls(dataset_dir='../datasets/Drawing2CAD-main')
    
    total = adapter.get_record_count()
    print(f'Total drawing2cad records found: {total}')
    
    batch = []
    count = 0
    start = time.time()
    
    for rec in adapter.iterate_records():
        if rec['record_id'] in db_ids:
            continue
        try:
            doc = adapter.to_cadir(rec)
            batch.append((doc, 'drawing2cad', None))
        except Exception as e:
            print(f"Error parsing {rec['record_id']}: {e}")
            
        if len(batch) >= 1000:
            index.bulk_index_documents(batch)
            count += len(batch)
            batch.clear()
            print(f'Indexed {count} drawing2cad records...')
            
    if batch:
        index.bulk_index_documents(batch)
        count += len(batch)
        
    print(f'Indexed {count} new drawing2cad records. Done in {time.time()-start:.2f}s')
    
    with index._get_connection() as conn:
        total_db = conn.execute('SELECT count(*) FROM cad_examples').fetchone()[0]
    print(f'Database now contains {total_db} items.')

if __name__ == '__main__':
    main()
