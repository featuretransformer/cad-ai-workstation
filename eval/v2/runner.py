"""
V2 Golden Benchmark runner.

Usage (from the repository root, using the backend virtualenv):

    python -m eval.v2.runner run --tag baseline-l2 --levels L2 --workers 3
    python -m eval.v2.runner report --run runs/baseline-l2
    python -m eval.v2.runner compare --baseline runs/baseline-l2 --candidate runs/improved-l2

The runner is resumable: records are appended to ``records.jsonl`` as each case
finishes, so an interrupted run can be continued with ``--resume``.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make ``python eval/v2/runner.py`` and ``python -m eval.v2.runner`` both work.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from eval.v2 import dataset, generate, metrics, report
else:
    from . import dataset, generate, metrics, report

from PIL import Image, ImageDraw, ImageFont


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(dataset.PROJECT_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "n/a"


def _append_record(path: Path, record: Dict[str, Any], lock: threading.Lock) -> None:
    line = json.dumps(record, ensure_ascii=False)
    with lock:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()


def _load_completed(path: Path) -> set:
    done = set()
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    done.add((r["id"], r["level"], r.get("sample", 0)))
                except Exception:
                    continue
    return done


def _gallery_image(case, level: str, record: Dict[str, Any], gen_stl: Optional[str], out_path: Path) -> None:
    ref = case.image(annotated=False)
    try:
        w, h = 512, 512
        panel_w = w * 2 + 24
        canvas = Image.new("RGB", (panel_w, h + 64), (245, 246, 248))
        if ref and ref.exists():
            canvas.paste(Image.open(ref).convert("RGB"), (0, 56))
        if gen_stl and Path(gen_stl).exists():
            gen_img = metrics.render_candidate(gen_stl)
            if gen_img is not None:
                canvas.paste(gen_img.convert("RGB"), (w + 24, 56))
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.load_default(size=14)
        except Exception:
            font = ImageFont.load_default()
        draw.text((8, 8), f"{case.id} [{case.tier}] {case.family} - {level}", fill=(20, 20, 20), font=font)
        draw.text(
            (8, 30),
            f"pass={record['overall_pass']}  iou={record['shape']['iou']:.3f}  "
            f"dim_err={record['dim']['max_error_pct']:.1f}%  place={record['placement']['corner_error_mm']:.2f}mm  "
            f"holes {record['holes']['generated_count']}/{record['holes']['expected_count']}",
            fill=(90, 90, 90),
            font=font,
        )
        draw.text((8, 40), "REFERENCE", fill=(30, 90, 30), font=font)
        draw.text((w + 32, 40), "GENERATED", fill=(160, 40, 40), font=font)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, "PNG")
    except Exception as exc:  # pragma: no cover - gallery is best effort
        print(f"  [gallery] {case.id} {level}: {exc}")


def run(args: argparse.Namespace) -> Path:
    cases = dataset.select_cases(
        dataset.load_cases(args.dataset),
        ids=args.ids.split(",") if args.ids else None,
        tiers=args.tiers.split(",") if args.tiers else None,
        families=args.families.split(",") if args.families else None,
        limit=args.limit,
    )
    levels = [l.strip().upper() for l in args.levels.split(",") if l.strip()]
    for lvl in levels:
        if lvl not in dataset.LEVELS:
            raise SystemExit(f"Unknown level {lvl}; choose from {dataset.LEVELS}")

    run_dir = Path(args.out_dir) if args.out_dir else dataset.PROJECT_ROOT / "eval" / "v2" / "runs" / args.tag
    run_dir.mkdir(parents=True, exist_ok=True)
    records_path = run_dir / "records.jsonl"
    gallery_dir = run_dir / "gallery"
    done = _load_completed(records_path) if args.resume else set()
    if not args.resume and records_path.exists():
        records_path.unlink()

    meta = {
        "tag": args.tag,
        "generator": args.generator,
        "input_mode": args.input_mode,
        "levels": levels,
        "cases": len(cases),
        "samples": args.samples,
        "dataset": str(Path(args.dataset).resolve()),
        "dataset_fingerprint": dataset.dataset_fingerprint(cases),
        "git_commit": _git_commit(),
        "started": datetime.now().isoformat(timespec="seconds"),
        "workers": args.workers,
    }
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    tasks: List[Tuple[Any, str, int]] = [
        (c, lvl, s) for c in cases for lvl in levels for s in range(args.samples)
    ]
    tasks = [t for t in tasks if (t[0].id, t[1], t[2]) not in done]

    print("=" * 78)
    print("V2 GOLDEN BENCHMARK")
    print("=" * 78)
    print(f"Run dir:     {run_dir}")
    print(f"Generator:   {args.generator} / {args.input_mode}")
    print(f"Cases:       {len(cases)} parts x {len(levels)} levels x {args.samples} sample(s) = {len(tasks)} to run")
    print(f"Workers:     {args.workers}")
    print(f"Fingerprint: {meta['dataset_fingerprint'][:16]}")
    print("=" * 78)

    gen = generate.get_generator(args.generator)
    lock = threading.Lock()
    started = time.time()
    completed = 0
    failures = 0

    def evaluate(task: Tuple[Any, str, int]) -> Dict[str, Any]:
        case, level, sample = task
        prompt = case.prompt(level)
        design_id = f"v2_{case.id.lower()}_{level.lower()}_s{sample}".replace("-", "_")
        image_path = None
        if args.input_mode in ("text+image", "image-only"):
            img = case.image(annotated=args.annotated_input)
            image_path = str(img) if img else None
        generation = gen(prompt, design_id, image_path=image_path, input_mode=args.input_mode)
        ref_img = None
        if case.image(annotated=False):
            try:
                ref_img = Image.open(case.image(annotated=False)).convert("RGB")
            except Exception:
                ref_img = None
        record = metrics.score_case(case, level, generation, ref_img)
        record["sample"] = sample
        return record

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(evaluate, t): t for t in tasks}
        for fut in as_completed(futures):
            case, level, sample = futures[fut]
            completed += 1
            try:
                record = fut.result()
            except Exception as exc:
                failures += 1
                record = {
                    "id": case.id,
                    "family": case.family,
                    "tier": case.tier,
                    "level": level,
                    "sample": sample,
                    "prompt": case.prompt(level),
                    "valid_solid": False,
                    "strict_pass": False,
                    "recognition_pass": False,
                    "overall_pass": False,
                    "pass_basis": "strict" if level in ("L2", "L3") else "recognition",
                    "dim": {"errors_pct": [], "max_error_pct": 100.0, "mean_error_pct": 100.0, "pass": False, "xy_swapped": False},
                    "volume": {"generated_mm3": 0.0, "expected_mm3": case.volume, "error_pct": 100.0, "pass": False},
                    "placement": {"min_delta_mm": [], "max_delta_mm": [], "corner_error_mm": 999.0, "centroid_error_mm": 999.0, "pass": False},
                    "holes": {"expected_count": case.hole_count, "generated_count": 0, "count_match": False,
                              "expected_diameters": case.hole_diameters, "generated_diameters": [],
                              "diameters_matched": 0, "diameters_expected": len(case.hole_diameters), "pass": False},
                    "shape": {"iou": 0.0, "chamfer_pct": 100.0, "render_ok": False},
                    "aspects": {"validity": 0.0, "dimensions": 0.0, "volume": 0.0, "positioning": 0.0, "topology": 0.0, "shape": 0.0},
                    "geometry": {"bbox_dims": [], "bbox_min": [], "bbox_max": []},
                    "expected": {"bbox_mm": case.bbox, "volume_mm3": case.volume,
                                 "placement_min": case.placement_min, "placement_max": case.placement_max,
                                 "holes": case.hole_count},
                    "generation": {"success": False, "latency_sec": 0.0, "error": f"{type(exc).__name__}: {exc}",
                                   "cadir_features": [], "design_id": None},
                    "traceback": traceback.format_exc()[-1500:],
                }

            _append_record(records_path, record, lock)

            if args.gallery and not record.get("overall_pass"):
                _gallery_image(
                    case,
                    level,
                    record,
                    record["generation"].get("stl_path"),
                    gallery_dir / f"{case.id}_{level}.png",
                )

            status = "PASS" if record.get("overall_pass") else "fail"
            print(
                f"[{completed:>3}/{len(tasks)}] {case.id:<7} {level}  {status}  "
                f"iou={record['shape']['iou']:.3f}  dim={record['dim']['max_error_pct']:5.1f}%  "
                f"place={record['placement']['corner_error_mm']:6.2f}mm  "
                f"holes={record['holes']['generated_count']}/{record['holes']['expected_count']}  "
                f"{record['generation'].get('latency_sec', 0):5.1f}s"
            )

    elapsed = time.time() - started
    records = report.load_records(run_dir)
    meta["finished"] = datetime.now().isoformat(timespec="seconds")
    meta["elapsed_sec"] = round(elapsed, 1)
    meta["scoring_failures"] = failures
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    agg = report.write_report(run_dir, records)
    print("-" * 78)
    print(f"Overall pass: {agg['overall_pass']:.1f}%   strict: {agg['strict_pass']:.1f}%   "
          f"valid: {agg['valid']:.1f}%   IoU: {agg['iou']:.3f}")
    print(f"Report: {run_dir / 'report.md'}")
    print(f"Elapsed: {elapsed:.0f}s")
    return run_dir


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="eval.v2.runner", description="V2 golden benchmark for the CAD pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run the benchmark")
    run_p.add_argument("--dataset", default=str(dataset.DATASET_FILE))
    run_p.add_argument("--levels", default="L2", help="Comma separated prompt levels (L0,L1,L2,L3)")
    run_p.add_argument("--tiers", default=None)
    run_p.add_argument("--families", default=None)
    run_p.add_argument("--ids", default=None)
    run_p.add_argument("--limit", type=int, default=None)
    run_p.add_argument("--samples", type=int, default=1)
    run_p.add_argument("--workers", type=int, default=3)
    run_p.add_argument("--generator", default="pipeline", choices=["pipeline", "core"])
    run_p.add_argument("--input-mode", default="text-only", choices=["text-only", "text+image", "image-only"])
    run_p.add_argument("--annotated-input", action="store_true", help="Use dimension-annotated renders as image input")
    run_p.add_argument("--tag", default=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    run_p.add_argument("--out-dir", default=None)
    run_p.add_argument("--resume", action="store_true")
    run_p.add_argument("--gallery", action="store_true", help="Write side-by-side images for failures")

    rep_p = sub.add_parser("report", help="Rebuild the report for an existing run")
    rep_p.add_argument("--run", required=True)

    res_p = sub.add_parser("rescore", help="Recompute pass flags of a stored run under the current thresholds")
    res_p.add_argument("--run", required=True)

    cmp_p = sub.add_parser("compare", help="Compare two runs case-for-case")
    cmp_p.add_argument("--baseline", required=True)
    cmp_p.add_argument("--candidate", required=True)
    cmp_p.add_argument("--out", default=None)

    args = parser.parse_args(argv)

    if args.command == "run":
        run(args)
    elif args.command == "rescore":
        run_dir = Path(args.run)
        recs = [metrics.rescore_stored(r) for r in report.load_records(run_dir)]
        with (run_dir / "records.jsonl").open("w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        agg = report.write_report(run_dir, recs)
        print(f"Rescored {len(recs)} records: overall pass {agg['overall_pass']:.1f}%  strict {agg['strict_pass']:.1f}%")
    elif args.command == "report":
        agg = report.write_report(args.run)
        print(f"Overall pass: {agg['overall_pass']:.1f}%  ({args.run}/report.md)")
    elif args.command == "compare":
        md = report.compare_runs(args.baseline, args.candidate)
        out = Path(args.out) if args.out else Path(args.candidate) / "comparison.md"
        out.write_text(md, encoding="utf-8")
        print(md)
        print(f"\nWritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
