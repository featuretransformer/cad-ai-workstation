"""
Aggregation, reporting and run-to-run comparison for the V2 benchmark.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .dataset import LEVELS, TIER_ORDER


def load_records(run_dir: Path | str) -> List[Dict[str, Any]]:
    run_dir = Path(run_dir)
    path = run_dir / "records.jsonl"
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_meta(run_dir: Path | str) -> Dict[str, Any]:
    p = Path(run_dir) / "run_meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    return sum(vals) / len(vals) if vals else 0.0


def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (percent)."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, (centre - half) * 100), min(100.0, (centre + half) * 100)


def aggregate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(records)
    if n == 0:
        return {"n": 0}

    def rate(key: str) -> float:
        return 100.0 * sum(1 for r in records if r.get(key)) / n

    passes = sum(1 for r in records if r.get("overall_pass"))
    lo, hi = _wilson_ci(passes, n)

    def levels_group(key: str) -> Dict[str, Dict[str, Any]]:
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in records:
            groups[str(r.get(key))].append(r)
        out = {}
        for g, items in groups.items():
            out[g] = {
                "n": len(items),
                "overall_pass": 100.0 * sum(1 for x in items if x.get("overall_pass")) / len(items),
                "strict_pass": 100.0 * sum(1 for x in items if x.get("strict_pass")) / len(items),
                "valid": 100.0 * sum(1 for x in items if x.get("valid_solid")) / len(items),
                "iou": _mean(x["shape"]["iou"] for x in items),
                "dim_pass": 100.0 * sum(1 for x in items if x["dim"]["pass"]) / len(items),
                "placement_pass": 100.0 * sum(1 for x in items if x["placement"]["pass"]) / len(items),
                "topology_pass": 100.0 * sum(1 for x in items if x["holes"]["pass"]) / len(items),
                "shape_pass": 100.0 * sum(1 for x in items if x["shape"]["iou"] >= 0.90) / len(items),
                "max_dim_err": _mean(x["dim"]["max_error_pct"] for x in items),
                "placement_err_mm": _mean(x["placement"]["corner_error_mm"] for x in items),
                "aspects": {
                    a: _mean(x["aspects"][a] for x in items) for a in ("validity", "dimensions", "volume", "positioning", "topology", "shape")
                },
            }
        return out

    by_level = levels_group("level")
    by_tier = levels_group("tier")
    by_family = levels_group("family")

    # Failure taxonomy (case may contribute to several buckets)
    taxonomy = Counter()
    for r in records:
        if r.get("overall_pass"):
            continue
        if not r.get("valid_solid"):
            taxonomy["invalid_solid"] += 1
            continue
        if not r["dim"]["pass"]:
            taxonomy["dimensions"] += 1
        if not r["placement"]["pass"]:
            taxonomy["placement"] += 1
        if not r["holes"]["pass"]:
            taxonomy["topology"] += 1
        if not r["volume"]["pass"]:
            taxonomy["volume"] += 1
        if r["shape"]["iou"] < 0.90:
            taxonomy["shape"] += 1

    latencies = sorted(r["generation"]["latency_sec"] or 0.0 for r in records)
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    return {
        "n": n,
        "overall_pass": 100.0 * passes / n,
        "overall_ci": [round(lo, 1), round(hi, 1)],
        "strict_pass": rate("strict_pass"),
        "valid": rate("valid_solid"),
        "iou": _mean(r["shape"]["iou"] for r in records),
        "shape_pass": 100.0 * sum(1 for r in records if r["shape"]["iou"] >= 0.90) / n,
        "dim_pass": 100.0 * sum(1 for r in records if r["dim"]["pass"]) / n,
        "placement_pass": 100.0 * sum(1 for r in records if r["placement"]["pass"]) / n,
        "topology_pass": 100.0 * sum(1 for r in records if r["holes"]["pass"]) / n,
        "volume_pass": 100.0 * sum(1 for r in records if r["volume"]["pass"]) / n,
        "mean_dim_err": _mean(r["dim"]["max_error_pct"] for r in records),
        "mean_placement_err": _mean(r["placement"]["corner_error_mm"] for r in records),
        "latency_p50": p50,
        "latency_p95": p95,
        "aspects": {
            a: _mean(r["aspects"][a] for r in records)
            for a in ("validity", "dimensions", "volume", "positioning", "topology", "shape")
        },
        "taxonomy": dict(taxonomy),
        "by_level": by_level,
        "by_tier": by_tier,
        "by_family": by_family,
    }


def _fmt(v: float, digits: int = 1) -> str:
    return f"{v:.{digits}f}"


def render_markdown(meta: Dict[str, Any], agg: Dict[str, Any], records: List[Dict[str, Any]]) -> str:
    level_order = [l for l in LEVELS if l in agg.get("by_level", {})]
    tier_order = [t for t in sorted(agg.get("by_tier", {}), key=lambda x: TIER_ORDER.get(x, 9))]

    lines: List[str] = []
    lines.append(f"# V2 Golden Benchmark - {meta.get('tag', 'run')}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**Pipeline:** `{meta.get('generator')}`  ")
    lines.append(f"**Input mode:** `{meta.get('input_mode')}`  ")
    lines.append(f"**Dataset fingerprint:** `{meta.get('dataset_fingerprint', '')[:16]}`  ")
    lines.append(f"**Cases:** {agg['n']}  ")
    lines.append(f"**Repository commit:** `{meta.get('git_commit', 'n/a')}`")
    lines.append("")
    lines.append("## 1. Headline")
    lines.append("")
    lines.append("| Metric | Score | 95% CI / note |")
    lines.append("| :--- | ---: | :--- |")
    lines.append(f"| **Overall Pass** | **{_fmt(agg['overall_pass'])}%** | {agg['overall_ci'][0]:.1f} - {agg['overall_ci'][1]:.1f}% |")
    lines.append(f"| Strict Pass (dims + placement + topology + volume + shape) | {_fmt(agg['strict_pass'])}% | all prompt levels |")
    lines.append(f"| Valid Solid | {_fmt(agg['valid'])}% | exported, watertight, volume > 0 |")
    lines.append(f"| Shape Match (silhouette IoU >= 0.90) | {_fmt(agg['shape_pass'])}% | mean IoU {agg['iou']:.3f} |")
    lines.append(f"| Dimensional Pass (<= 2% per axis) | {_fmt(agg['dim_pass'])}% | mean max error {agg['mean_dim_err']:.1f}% |")
    lines.append(f"| Placement Pass (corner <= 1 mm) | {_fmt(agg['placement_pass'])}% | mean error {agg['mean_placement_err']:.2f} mm |")
    lines.append(f"| Topology Pass (hole count + diameters) | {_fmt(agg['topology_pass'])}% | |")
    lines.append(f"| Volume Pass (<= 5%) | {_fmt(agg['volume_pass'])}% | |")
    lines.append(f"| Latency p50 / p95 | {agg['latency_p50']:.1f}s / {agg['latency_p95']:.1f}s | |")
    lines.append("")

    lines.append("## 2. Aspect scores (0-1, higher is better)")
    lines.append("")
    lines.append("| Validity | Dimensions | Volume | Positioning | Topology | Shape |")
    lines.append("| ---: | ---: | ---: | ---: | ---: | ---: |")
    a = agg["aspects"]
    lines.append(
        f"| {a['validity']:.3f} | {a['dimensions']:.3f} | {a['volume']:.3f} | "
        f"{a['positioning']:.3f} | {a['topology']:.3f} | {a['shape']:.3f} |"
    )
    lines.append("")

    lines.append("## 3. By prompt level")
    lines.append("")
    lines.append("| Level | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |")
    lines.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for lvl in level_order:
        g = agg["by_level"][lvl]
        lines.append(
            f"| {lvl} | {g['n']} | {g['overall_pass']:.1f}% | {g['strict_pass']:.1f}% | {g['valid']:.1f}% | "
            f"{g['iou']:.3f} | {g['dim_pass']:.1f}% | {g['placement_pass']:.1f}% | {g['topology_pass']:.1f}% |"
        )
    lines.append("")

    lines.append("## 4. By difficulty tier")
    lines.append("")
    lines.append("| Tier | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |")
    lines.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for tier in tier_order:
        g = agg["by_tier"][tier]
        lines.append(
            f"| {tier} | {g['n']} | {g['overall_pass']:.1f}% | {g['strict_pass']:.1f}% | {g['valid']:.1f}% | "
            f"{g['iou']:.3f} | {g['dim_pass']:.1f}% | {g['placement_pass']:.1f}% | {g['topology_pass']:.1f}% |"
        )
    lines.append("")

    lines.append("## 5. By part family")
    lines.append("")
    lines.append("| Family | n | Overall | Strict | IoU | Dim pass | Topology |")
    lines.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for fam in sorted(agg["by_family"]):
        g = agg["by_family"][fam]
        lines.append(
            f"| {fam} | {g['n']} | {g['overall_pass']:.0f}% | {g['strict_pass']:.0f}% | "
            f"{g['iou']:.3f} | {g['dim_pass']:.0f}% | {g['topology_pass']:.0f}% |"
        )
    lines.append("")

    lines.append("## 6. Failure taxonomy")
    lines.append("")
    lines.append("| Cause | Failures |")
    lines.append("| :--- | ---: |")
    for cause, count in sorted(agg["taxonomy"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {cause} | {count} |")
    if not agg["taxonomy"]:
        lines.append("| (none) | 0 |")
    lines.append("")

    # Worst cases
    worst = sorted(records, key=lambda r: (r.get("overall_pass", False), r["shape"]["iou"], r["dim"]["max_error_pct"]))[:12]
    lines.append("## 7. Lowest-scoring cases")
    lines.append("")
    lines.append("| Part | Level | Pass | IoU | Dim err % | Placement mm | Holes gen/exp | Error |")
    lines.append("| :--- | :--- | :---: | ---: | ---: | ---: | :---: | :--- |")
    for r in worst:
        err = (r["generation"].get("error") or "").replace("|", "/")[:90]
        lines.append(
            f"| {r['id']} | {r['level']} | {'Y' if r['overall_pass'] else 'N'} | {r['shape']['iou']:.3f} | "
            f"{r['dim']['max_error_pct']:.1f} | {r['placement']['corner_error_mm']:.2f} | "
            f"{r['holes']['generated_count']}/{r['holes']['expected_count']} | {err} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(run_dir: Path | str, records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    run_dir = Path(run_dir)
    records = records if records is not None else load_records(run_dir)
    meta = load_meta(run_dir)
    if not records:
        raise SystemExit(f"No records found in {run_dir}")

    agg = aggregate(records)
    report_md = render_markdown(meta, agg, records)
    (run_dir / "report.md").write_text(report_md, encoding="utf-8")

    # CSV of flat per-case results
    flat_fields = [
        "id", "family", "tier", "level", "overall_pass", "strict_pass", "recognition_pass",
        "valid_solid", "iou", "chamfer_pct", "dim_max_err_pct", "dim_pass", "vol_err_pct",
        "placement_corner_mm", "placement_pass", "holes_gen", "holes_exp", "topology_pass",
        "latency_sec", "error",
    ]
    with (run_dir / "results.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=flat_fields)
        w.writeheader()
        for r in records:
            w.writerow({
                "id": r["id"],
                "family": r["family"],
                "tier": r["tier"],
                "level": r["level"],
                "overall_pass": int(bool(r["overall_pass"])),
                "strict_pass": int(bool(r["strict_pass"])),
                "recognition_pass": int(bool(r["recognition_pass"])),
                "valid_solid": int(bool(r["valid_solid"])),
                "iou": r["shape"]["iou"],
                "chamfer_pct": r["shape"]["chamfer_pct"],
                "dim_max_err_pct": r["dim"]["max_error_pct"],
                "dim_pass": int(bool(r["dim"]["pass"])),
                "vol_err_pct": r["volume"]["error_pct"],
                "placement_corner_mm": r["placement"]["corner_error_mm"],
                "placement_pass": int(bool(r["placement"]["pass"])),
                "holes_gen": r["holes"]["generated_count"],
                "holes_exp": r["holes"]["expected_count"],
                "topology_pass": int(bool(r["holes"]["pass"])),
                "latency_sec": r["generation"].get("latency_sec"),
                "error": (r["generation"].get("error") or "").replace("\n", " ")[:200],
            })

    (run_dir / "summary.json").write_text(json.dumps(agg, indent=2), encoding="utf-8")
    return agg


def compare_runs(run_a: Path | str, run_b: Path | str) -> str:
    """Markdown table comparing two runs case-for-case (b - a deltas)."""
    a = {(r["id"], r["level"]): r for r in load_records(run_a)}
    b = {(r["id"], r["level"]): r for r in load_records(run_b)}
    keys = sorted(set(a) & set(b))
    if not keys:
        return "No overlapping cases between the two runs."

    agg_a = aggregate(list(a[k] for k in keys))
    agg_b = aggregate(list(b[k] for k in keys))

    lines = ["# Run comparison", "", f"**Baseline:** `{run_a}`  ", f"**Candidate:** `{run_b}`  ", f"**Common cases:** {len(keys)}", ""]
    lines.append("| Metric | Baseline | Candidate | Delta |")
    lines.append("| :--- | ---: | ---: | ---: |")
    for label, key in [
        ("Overall pass %", "overall_pass"),
        ("Strict pass %", "strict_pass"),
        ("Valid %", "valid"),
        ("Shape match %", "shape_pass"),
        ("Dimensions pass %", "dim_pass"),
        ("Placement pass %", "placement_pass"),
        ("Topology pass %", "topology_pass"),
        ("Mean IoU", "iou"),
        ("Mean dim error %", "mean_dim_err"),
        ("Mean placement error mm", "mean_placement_err"),
    ]:
        va, vb = agg_a[key], agg_b[key]
        lines.append(f"| {label} | {va:.2f} | {vb:.2f} | {vb - va:+.2f} |")
    lines.append("")
    lines.append("## Per-level")
    lines.append("")
    lines.append("| Level | n | Overall (a -> b) | IoU (a -> b) | Dim pass (a -> b) |")
    lines.append("| :--- | ---: | :--- | :--- | :--- |")
    for lvl in LEVELS:
        if lvl not in agg_a["by_level"] or lvl not in agg_b["by_level"]:
            continue
        ga, gb = agg_a["by_level"][lvl], agg_b["by_level"][lvl]
        lines.append(
            f"| {lvl} | {ga['n']} | {ga['overall_pass']:.1f}% -> {gb['overall_pass']:.1f}% | "
            f"{ga['iou']:.3f} -> {gb['iou']:.3f} | {ga['dim_pass']:.1f}% -> {gb['dim_pass']:.1f}% |"
        )
    lines.append("")
    improved = [k for k in keys if not a[k]["overall_pass"] and b[k]["overall_pass"]]
    regressed = [k for k in keys if a[k]["overall_pass"] and not b[k]["overall_pass"]]
    lines.append(f"**Fixed:** {len(improved)} cases  ")
    lines.append(f"**Regressed:** {len(regressed)} cases")
    if regressed:
        lines.append("")
        lines.append("| Regressed case | Reason |")
        lines.append("| :--- | :--- |")
        for k in regressed[:20]:
            r = b[k]
            lines.append(f"| {k[0]} {k[1]} | iou {r['shape']['iou']:.3f}, dim err {r['dim']['max_error_pct']:.1f}%, placement {r['placement']['corner_error_mm']:.2f} mm |")
    return "\n".join(lines) + "\n"
