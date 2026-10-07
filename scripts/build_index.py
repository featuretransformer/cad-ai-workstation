"""
CAD Knowledge Base Indexing Pipeline.
Extracts, translates, and indexes parametric CAD models from local datasets
(BenchCAD, DeepCAD, Fusion360) into SQLite knowledge.db for few-shot retrieval.
"""
import argparse
from pathlib import Path
import sys
import time

# Ensure backend root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from datasets.registry import get_available_adapters, get_adapter
from retrieval.index import KnowledgeIndex
from config import settings


def build_knowledge_index(
    db_path: Optional_Path = None,
    limit_per_dataset: int = 50,
    clear_existing: bool = False,
    target_datasets: Optional[List[str]] = None,
) -> None:
    """
    Populates SQLite knowledge base from available local datasets.
    """
    db_file = Path(db_path) if db_path else Path(settings.knowledge_db_path)
    print(f"[*] Initializing Knowledge Index at: {db_file}")

    index = KnowledgeIndex(db_file)
    if clear_existing:
        print("[*] Clearing existing knowledge index records...")
        index.clear_all()

    available = get_available_adapters(datasets_dir=root_dir / "datasets")
    print(f"[*] Discovered available datasets: {list(available.keys())}")

    datasets_to_process = target_datasets if target_datasets else list(available.keys())
    start_time = time.time()
    total_indexed = 0

    for name in datasets_to_process:
        if name not in available:
            print(f"[-] Dataset '{name}' is not available on disk. Skipping.")
            continue

        adapter = available[name]
        print(f"\n[+] Ingesting from {name} (Limit: {limit_per_dataset})...")

        count = 0
        batch = []
        for record in adapter.iterate_records(limit=limit_per_dataset):
            try:
                doc = adapter.to_cadir(record)
                batch.append((doc, name, None))
                count += 1
            except Exception as e:
                print(f"    [!] Error translating record {record.get('record_id')}: {e}")

        if batch:
            indexed = index.bulk_index_documents(batch)
            total_indexed += indexed
            print(f"    [OK] Successfully indexed {indexed} exemplars from {name}.")

    elapsed = time.time() - start_time
    total_docs = index.get_document_count()
    families = index.get_family_counts()

    print("\n" + "=" * 60)
    print("KNOWLEDGE BASE INDEXING SUMMARY")
    print("=" * 60)
    print(f"Total documents in index: {total_docs}")
    print(f"Time taken: {elapsed:.2f} seconds")
    print(f"Database file size: {db_file.stat().st_size / 1024:.1f} KB")
    print("\nTop Component Families:")
    for fam, cnt in list(families.items())[:10]:
        print(f"  - {fam or 'unclassified'}: {cnt} exemplars")
    print("=" * 60)


if __name__ == "__main__":
    from typing import Optional as Optional_Path, List

    parser = argparse.ArgumentParser(description="Build CADIR Knowledge Base SQLite Index")
    parser.add_argument("--db-path", type=str, default=None, help="Target SQLite DB path")
    parser.add_argument("--limit", type=int, default=50, help="Max records per dataset")
    parser.add_argument("--clear", action="store_true", help="Clear existing DB records first")
    parser.add_argument("--datasets", type=str, default=None, help="Comma-separated dataset names")

    args = parser.parse_args()
    target_ds = [d.strip().lower() for d in args.datasets.split(",")] if args.datasets else None

    build_knowledge_index(
        db_path=args.db_path,
        limit_per_dataset=args.limit,
        clear_existing=args.clear,
        target_datasets=target_ds,
    )
