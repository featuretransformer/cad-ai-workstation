"""
Merges per-case records from a patch run into a base run.

Useful when a few cases are re-run after a targeted fix without paying for the
whole benchmark again:

    python -m eval.v2.merge --base eval/v2/runs/improved_l2 --patch eval/v2/runs/patch_e09_m02
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from eval.v2 import report
else:
    from . import report


def merge(base_dir: Path, patch_dir: Path) -> int:
    base_records = report.load_records(base_dir)
    patch_records = report.load_records(patch_dir)
    if not patch_records:
        print("Patch run has no records")
        return 1

    key = lambda r: (r["id"], r["level"], r.get("sample", 0))
    index = {key(r): i for i, r in enumerate(base_records)}
    replaced = added = 0
    for r in patch_records:
        k = key(r)
        if k in index:
            base_records[index[k]] = r
            replaced += 1
        else:
            base_records.append(r)
            added += 1

    out = base_dir / "records.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for r in base_records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    meta = report.load_meta(base_dir)
    meta["merged_from"] = str(patch_dir)
    meta["merged_records"] = {"replaced": replaced, "added": added}
    (base_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    agg = report.write_report(base_dir, base_records)
    print(f"Merged {replaced} replaced + {added} new records into {base_dir}")
    print(f"Overall pass: {agg['overall_pass']:.1f}%  strict: {agg['strict_pass']:.1f}%")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="eval.v2.merge")
    p.add_argument("--base", required=True)
    p.add_argument("--patch", required=True)
    a = p.parse_args()
    return merge(Path(a.base), Path(a.patch))


if __name__ == "__main__":
    raise SystemExit(main())
