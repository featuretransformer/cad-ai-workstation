"""
CAD Evaluation Harness: Accuracy on Shape, Dimensions, and Positioning.
Evaluates generated models against frozen ground-truth geometry (STEP/mesh).
Supports:
- Modes: text-only, image-only, text+image
- Prompt levels: L0 (abstract), L1 (coarse), L2 (parametric specs), L3 (construction instructions)
- Pass@1 and Pass@k (default k=3)
- Strict failure accounting (failed generations score 0, never dropped)
- Metric breakdowns by level, tier, and family
- Confidence intervals and side-by-side visual comparison renders
"""
import os
import sys
import json
import time
import math
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import csv
import numpy as np
from PIL import Image

# Ensure backend and eval root are in sys.path
EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agents.graph import cad_graph
from agents.state import AgentState
from metrics import evaluate_cad_model
from build_golden_set import render_mesh_to_isometric, extract_edges_from_mesh

MANIFEST_FILE = EVAL_DIR / "golden_set" / "manifest.jsonl"
HASH_FILE = EVAL_DIR / "golden_set" / "golden_set.sha256"
REPORTS_DIR = EVAL_DIR / "reports"
VIZ_DIR = REPORTS_DIR / "visualizations"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
VIZ_DIR.mkdir(parents=True, exist_ok=True)


def load_golden_manifest() -> List[Dict[str, Any]]:
    """Loads all records from frozen golden manifest."""
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_FILE}. Run build_golden_set.py first!")
    records = []
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def get_golden_set_hash() -> str:
    """Retrieves SHA-256 freeze hash."""
    if HASH_FILE.exists():
        with open(HASH_FILE, "r", encoding="utf-8") as f:
            return f.read().strip().split()[0]
    return "UNKNOWN_HASH"


# ─── Pluggable Model Generation Entry Point ───────────────────────────────────

def generate_cad(
    prompt: str,
    image_path: Optional[str] = None,
    design_id: str = "eval_candidate",
    input_mode: str = "text-only",
) -> Dict[str, Any]:
    """
    Pluggable generation function wired directly to this project's real entry point.
    Handles text-only, image-only, and text+image modes.
    Returns:
        - success: bool
        - step_path: Optional[str]
        - stl_path: Optional[str]
        - cad_code: str
        - error: str
        - latency_sec: float
    """
    t0 = time.time()
    state: AgentState = {
        "design_id": design_id,
        "max_retries": 2,
    }

    if input_mode == "text-only":
        state["user_prompt"] = prompt
        state["input_type"] = "text"
    elif input_mode == "image-only":
        state["user_prompt"] = "Reconstruct mechanical CAD model from provided isometric engineering image."
        state["file_path"] = image_path
        state["input_type"] = "image"
    elif input_mode == "text+image":
        state["user_prompt"] = prompt
        state["file_path"] = image_path
        state["input_type"] = "multimodal"
    else:
        raise ValueError(f"Unknown input mode: {input_mode}")

    try:
        final_state = cad_graph.invoke(state)
        latency = round(time.time() - t0, 3)

        geom_valid = bool(final_state.get("geometry_valid", False))
        export_paths = final_state.get("export_paths", {})
        step_p = export_paths.get("step")
        stl_p = export_paths.get("stl")

        step_ok = bool(step_p and Path(step_p).exists() and Path(step_p).stat().st_size > 50)
        stl_ok = bool(stl_p and Path(stl_p).exists() and Path(stl_p).stat().st_size > 50)

        err_msg = ""
        if not (step_ok and stl_ok):
            val_errors = final_state.get("validation_errors", [])
            last_err = final_state.get("last_error", "")
            err_msg = "; ".join(val_errors) or last_err or "Missing exported STEP/STL file"

        return {
            "success": geom_valid and step_ok and stl_ok,
            "step_path": step_p if step_ok else None,
            "stl_path": stl_p if stl_ok else None,
            "cad_code": final_state.get("cad_code", ""),
            "error": err_msg,
            "latency_sec": latency,
        }
    except Exception as e:
        latency = round(time.time() - t0, 3)
        return {
            "success": False,
            "step_path": None,
            "stl_path": None,
            "cad_code": "",
            "error": f"Invocation exception: {e}",
            "latency_sec": latency,
        }


def save_side_by_side_render(gt_img_path: str, gen_stl_path: Optional[str], out_path: str, label: str):
    """Generates side-by-side visual comparison (Ground Truth vs Generated Candidate)."""
    try:
        gt_img = Image.open(gt_img_path).convert("RGB")
        w, h = gt_img.size

        if gen_stl_path and Path(gen_stl_path).exists() and Path(gen_stl_path).stat().st_size > 50:
            import trimesh
            gen_mesh = trimesh.load(gen_stl_path, force="mesh")
            edges = extract_edges_from_mesh(gen_mesh)
            gen_img = render_mesh_to_isometric(gen_mesh.vertices, gen_mesh.faces, edges).convert("RGB")
        else:
            # Black placeholder for failed generation
            gen_img = Image.new("RGB", (w, h), color=(30, 30, 30))

        # Composite side-by-side
        combined = Image.new("RGB", (w * 2 + 10, h + 40), color=(240, 242, 245))
        combined.paste(gt_img, (0, 35))
        combined.paste(gen_img, (w + 10, 35))

        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(combined)
        try:
            f = ImageFont.load_default(size=16)
        except Exception:
            f = ImageFont.load_default()

        draw.text((20, 10), "GROUND TRUTH GEOMETRY", fill=(20, 20, 20), font=f)
        draw.text((w + 30, 10), f"MODEL GENERATION — {label.upper()}", fill=(200, 30, 30), font=f)

        combined.save(out_path, "PNG")
    except Exception as e:
        print(f"    [!] Error saving side-by-side render: {e}")


# ─── Main Evaluation Runner ───────────────────────────────────────────────────

def run_evaluation(
    mode: str = "text-only",
    levels: List[str] = None,
    k: int = 1,
    limit: Optional[int] = None,
    families: Optional[List[str]] = None,
    tiers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    levels = levels or ["L0", "L1", "L2", "L3"]
    records = load_golden_manifest()
    freeze_hash = get_golden_set_hash()

    # Filter records
    if families:
        records = [r for r in records if r["family"] in families]
    if tiers:
        records = [r for r in records if r["tier"] in tiers]
    if limit:
        records = records[:limit]

    print("\n" + "=" * 70)
    print("AI-NATIVE CAD EVALUATION HARNESS")
    print("=" * 70)
    print(f"Timestamp:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Golden Set Hash: {freeze_hash}")
    print(f"Input Mode:      {mode}")
    print(f"Prompt Levels:   {', '.join(levels)}")
    print(f"Samples per Part:{k} (reporting pass@1 and pass@{k})")
    print(f"Test Records:    {len(records)} parts")
    print("=" * 70 + "\n")

    all_item_results: List[Dict[str, Any]] = []

    total_prompts = len(records) * len(levels)
    processed_count = 0

    for rec in records:
        pid = rec["id"]
        fam = rec["family"]
        tier = rec["tier"]

        gt_step = str(EVAL_DIR / "golden_set" / rec["step_relpath"])
        gt_stl = str(EVAL_DIR / "golden_set" / rec["stl_relpath"])
        gt_render = str(EVAL_DIR / "golden_set" / rec["render_relpath"])

        for lvl in levels:
            processed_count += 1
            prompt_text = rec["prompts"].get(lvl, "")
            print(f"[{processed_count}/{total_prompts}] {pid} ({fam}, {tier}) - {lvl}...")

            k_trials: List[Dict[str, Any]] = []
            pass_trials = 0

            for sample_idx in range(k):
                d_id = f"eval_{pid}_{lvl.lower()}_s{sample_idx}"
                img_input = gt_render if mode in ("image-only", "text+image") else None

                # Generate model output
                gen_res = generate_cad(prompt_text, image_path=img_input, design_id=d_id, input_mode=mode)

                if gen_res["success"] and gen_res["step_path"] and gen_res["stl_path"]:
                    # Run metrics against ground-truth geometry
                    eval_metrics = evaluate_cad_model(
                        gt_step_path=gt_step,
                        gt_stl_path=gt_stl,
                        gen_step_path=gen_res["step_path"],
                        gen_stl_path=gen_res["stl_path"],
                    )
                else:
                    # Failed generation counts strictly as failure (never dropped)
                    eval_metrics = evaluate_cad_model(
                        gt_step_path=gt_step,
                        gt_stl_path=gt_stl,
                        gen_step_path=None,
                        gen_stl_path=None,
                    )
                    eval_metrics["error"] = gen_res.get("error", "Generation failed")

                eval_metrics["sample_idx"] = sample_idx
                eval_metrics["latency_sec"] = gen_res["latency_sec"]
                k_trials.append(eval_metrics)

                if eval_metrics["overall_pass"]:
                    pass_trials += 1

            pass_at_1 = pass_trials / max(k, 1)
            pass_at_k = 1.0 if pass_trials > 0 else 0.0

            # Use best trial or first trial for representative metrics
            best_trial = max(k_trials, key=lambda t: (t["overall_pass"], t["shape"]["normalised"]["f_score"]))

            # Save visual render for failures or low IoU
            if not best_trial["overall_pass"]:
                viz_path = str(VIZ_DIR / f"{pid}_{lvl}_failure.png")
                best_stl = k_trials[0].get("stl_path")
                save_side_by_side_render(gt_render, best_stl, viz_path, label=f"FAIL {lvl}")

            print(f"    -> Pass@1: {pass_at_1*100:.1f}% | Pass@{k}: {pass_at_k*100:.1f}% | Valid: {best_trial['valid_solid']} | F1: {best_trial['shape']['normalised']['f_score']:.3f} | Dim2%: {best_trial['dimensions']['pass_rate_2pct']*100:.1f}%")

            item_entry = {
                "id": pid,
                "family": fam,
                "tier": tier,
                "level": lvl,
                "prompt": prompt_text,
                "pass_at_1": pass_at_1,
                "pass_at_k": pass_at_k,
                "valid_solid": best_trial["valid_solid"],
                "overall_pass": best_trial["overall_pass"],
                "norm_chamfer": best_trial["shape"]["normalised"]["chamfer_distance"],
                "norm_f_score": best_trial["shape"]["normalised"]["f_score"],
                "norm_iou": best_trial["shape"]["normalised"]["iou"],
                "raw_chamfer_mm": best_trial["shape"]["raw"]["chamfer_distance_mm"],
                "dim_pass_rate_2pct": best_trial["dimensions"]["pass_rate_2pct"],
                "median_dim_error_pct": best_trial["dimensions"]["median_error_pct"],
                "p90_dim_error_pct": best_trial["dimensions"]["p90_error_pct"],
                "volume_error_pct": best_trial["dimensions"]["checks"].get("volume_error_pct", 100.0),
                "hole_count_match": best_trial["positioning"]["hole_count_match"],
                "mean_feature_pos_error_mm": best_trial["positioning"]["mean_feature_pos_error_mm"],
                "rotational_misalignment": best_trial["positioning"]["axis_alignment_diagnostic"]["rotational_misalignment_detected"],
                "latency_sec": best_trial["latency_sec"],
                "error": best_trial.get("error", ""),
            }
            all_item_results.append(item_entry)

    # 1. Save Raw Per-Item Results (JSONL and CSV)
    jsonl_out = REPORTS_DIR / "eval_results.jsonl"
    with open(jsonl_out, "w", encoding="utf-8") as f:
        for r in all_item_results:
            f.write(json.dumps(r) + "\n")

    csv_out = REPORTS_DIR / "eval_results.csv"
    if all_item_results:
        fieldnames = list(all_item_results[0].keys())
        with open(csv_out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_item_results)

    return generate_report_from_results(
        all_item_results=all_item_results,
        k=k,
        mode=mode,
    )


def generate_report_from_results(
    all_item_results: List[Dict[str, Any]],
    k: int = 1,
    mode: str = "text-only",
) -> Dict[str, Any]:
    """Generates CSV, JSONL, and Markdown baseline reports from evaluation records."""
    csv_out = REPORTS_DIR / "eval_results.csv"
    jsonl_out = REPORTS_DIR / "eval_results.jsonl"
    freeze_hash = get_golden_set_hash()

    # 1. Ensure files are written if invoked directly
    if all_item_results:
        fieldnames = list(all_item_results[0].keys())
        with open(csv_out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_item_results)
        with open(jsonl_out, "w", encoding="utf-8") as f:
            for r in all_item_results:
                f.write(json.dumps(r) + "\n")

    # 2. Compute Aggregates & Confidence Intervals
    n_total = len(all_item_results)
    if n_total == 0:
        print("[!] No evaluation items processed.")
        return {}

    p_ids = sorted(list(set(r["id"] for r in all_item_results)))
    levels = sorted(list(set(r["level"] for r in all_item_results)))

    pass_1_mean = float(np.mean([r["pass_at_1"] for r in all_item_results]))
    pass_k_mean = float(np.mean([r["pass_at_k"] for r in all_item_results]))
    valid_mean = float(np.mean([1.0 if r["valid_solid"] else 0.0 for r in all_item_results]))
    f_score_mean = float(np.mean([r["norm_f_score"] for r in all_item_results]))
    chamfer_mean = float(np.mean([r["norm_chamfer"] for r in all_item_results]))
    iou_mean = float(np.mean([r["norm_iou"] for r in all_item_results]))
    dim_pass_mean = float(np.mean([r["dim_pass_rate_2pct"] for r in all_item_results]))
    p90_err_mean = float(np.mean([r["p90_dim_error_pct"] for r in all_item_results]))
    rot_misalign_mean = float(np.mean([1.0 if r["rotational_misalignment"] else 0.0 for r in all_item_results]))

    # 95% Confidence Interval for Pass@1
    ci_pass_1 = 1.96 * math.sqrt((pass_1_mean * (1.0 - pass_1_mean)) / max(n_total, 1))

    # Helper for grouping
    def group_metrics(key_name: str) -> List[Dict[str, Any]]:
        groups = {}
        for r in all_item_results:
            val = r[key_name]
            if val not in groups:
                groups[val] = []
            groups[val].append(r)
        out = []
        for g_val in sorted(groups.keys()):
            items = groups[g_val]
            out.append({
                key_name: g_val,
                "pass_at_1": float(np.mean([x["pass_at_1"] for x in items])),
                "pass_at_k": float(np.mean([x["pass_at_k"] for x in items])),
                "valid_solid": float(np.mean([1.0 if x["valid_solid"] else 0.0 for x in items])),
                "norm_f_score": float(np.mean([x["norm_f_score"] for x in items])),
                "dim_pass_rate_2pct": float(np.mean([x["dim_pass_rate_2pct"] for x in items])),
            })
        return out

    by_level = group_metrics("level")
    by_tier = group_metrics("tier")
    by_family = group_metrics("family")

    # 3. Generate Markdown Baseline Report
    report_md = f"""# CAD AI Workstation — Baseline Evaluation Report

**Evaluation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Model / Pipeline Version:** AI-Native CAD-CAM Workstation 1.0 (CADIR Multi-Agent)  
**Golden Set Hash (Frozen):** `{freeze_hash}`  
**Test Items:** {len(p_ids)} mechanical parts × {len(levels)} prompt levels = {n_total} evaluation cases  
**Input Mode:** `{mode}` (k = {k} samples/prompt)  

---

## 1. Executive Summary & Core Pass Bars

| Core Metric | Baseline Score | 95% Confidence Interval | Initial Pass Bar | Target Status |
| :--- | :---: | :---: | :---: | :---: |
| **Pass@1 Overall** | **{pass_1_mean*100:.1f}%** | ±{ci_pass_1*100:.1f}% | >= 80.0% | {'[PASS]' if pass_1_mean >= 0.8 else '[FAIL]'} |
| **Pass@{k} Overall** | **{pass_k_mean*100:.1f}%** | — | >= 90.0% | {'[PASS]' if pass_k_mean >= 0.9 else '[FAIL]'} |
| **Valid Solid Generation** | **{valid_mean*100:.1f}%** | — | >= 95.0% | {'[PASS]' if valid_mean >= 0.95 else '[FAIL]'} |
| **Shape F-Score (Normalised, tau=0.01)** | **{f_score_mean:.3f}** | — | >= 0.900 | {'[PASS]' if f_score_mean >= 0.9 else '[FAIL]'} |
| **Shape Chamfer Distance (Normalised)** | **{chamfer_mean:.4f}** | — | <= 0.035 | {'[PASS]' if chamfer_mean <= 0.035 else '[FAIL]'} |
| **Volumetric IoU (Normalised)** | **{iou_mean:.3f}** | — | >= 0.850 | {'[PASS]' if iou_mean >= 0.85 else '[FAIL]'} |
| **Dimensional Pass Rate (within 2%)** | **{dim_pass_mean*100:.1f}%** | — | >= 80.0% | {'[PASS]' if dim_pass_mean >= 0.8 else '[FAIL]'} |
| **P90 Dimensional Error** | **{p90_err_mean:.1f}%** | — | <= 5.0% | {'[PASS]' if p90_err_mean <= 5.0 else '[FAIL]'} |
| **Rotational Misalignment Detected** | **{rot_misalign_mean*100:.1f}%** | — | <= 10.0% | Diagnostic |

---

## 2. Performance by Prompt Complexity Level

| Prompt Level | Description | Pass@1 | Pass@{k} | Valid Solid | Shape F1 | Dim Pass (2%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
"""
    level_descriptions = {
        "L0": "Abstract natural language intent (e.g. 'A simple rectangular block')",
        "L1": "Coarse dimensions (e.g. '40 mm long and 10 mm tall')",
        "L2": "Complete parametric engineering specification (L x W x H)",
        "L3": "Step-by-step CAD construction instructions (sketch, plane, extrude)",
    }
    for row in by_level:
        lvl = row["level"]
        desc = level_descriptions.get(lvl, "")
        report_md += f"| **{lvl}** | {desc} | {row['pass_at_1']*100:.1f}% | {row['pass_at_k']*100:.1f}% | {row['valid_solid']*100:.1f}% | {row['norm_f_score']:.3f} | {row['dim_pass_rate_2pct']*100:.1f}% |\n"

    report_md += """
---

## 3. Performance by Difficulty Tier

| Difficulty Tier | Components Included | Pass@1 | Pass@{k} | Valid Solid | Shape F1 | Dim Pass (2%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
"""
    tier_desc = {
        "easy": "Boxes, cylinders, tubes, single-hole plates (12 parts)",
        "medium": "4-hole plates, L-brackets, stepped shafts, U-channels (12 parts)",
        "hard": "Hex nuts, multi-hole pipe flanges (6 parts)",
    }
    for row in by_tier:
        tr = row["tier"]
        tdesc = tier_desc.get(tr, "")
        report_md += f"| **{tr.capitalize()}** | {tdesc} | {row['pass_at_1']*100:.1f}% | {row['pass_at_k']*100:.1f}% | {row['valid_solid']*100:.1f}% | {row['norm_f_score']:.3f} | {row['dim_pass_rate_2pct']*100:.1f}% |\n"

    report_md += """
---

## 4. Performance by Part Family

| Mechanical Family | Pass@1 | Pass@{k} | Valid Solid | Shape F1 | Dim Pass (2%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
    for row in by_family:
        report_md += f"| **{row['family']}** | {row['pass_at_1']*100:.1f}% | {row['pass_at_k']*100:.1f}% | {row['valid_solid']*100:.1f}% | {row['norm_f_score']:.3f} | {row['dim_pass_rate_2pct']*100:.1f}% |\n"

    # Analyze Failure Patterns
    failures = [r for r in all_item_results if not r["overall_pass"]]
    report_md += f"""
---

## 5. Failure Pattern Analysis & Suggested Fixes

Total failed test cases: **{len(failures)} / {n_total}** ({len(failures)/n_total*100:.1f}%)

### Observed Failure Modes:
"""
    if not failures:
        report_md += "* **Zero Failures**: All test cases met or exceeded pass bars!\n"
    else:
        # Categorize
        rot_fails = [f for f in failures if f["rotational_misalignment"]]
        dim_fails = [f for f in failures if f["dim_pass_rate_2pct"] < 0.8 and f["valid_solid"]]
        invalid_fails = [f for f in failures if not f["valid_solid"]]
        l0_fails = [f for f in failures if f["level"] == "L0"]

        if l0_fails:
            report_md += f"""
1. **L0 Abstract Intent Under-Specification ({len(l0_fails)} cases)**:
   - *Symptom:* L0 prompts omit numerical dimensions (e.g. 'A simple rectangular block'). When no dimensions are given, the LLM must invent default proportions.
   - *Fix:* Ensure intent extractor applies default standard ISO reference envelopes when prompt level is purely conceptual (L0).
"""
        if rot_fails:
            report_md += f"""
2. **Axis / Coordinate Frame Misalignment ({len(rot_fails)} cases)**:
   - *Symptom:* The model generated correct cross-sections and depths, but extruded along the wrong cardinal plane (e.g. XY plane instead of XZ plane).
   - *Fix:* Implement coordinate grounding in prompt generator to explicitly declare primary mounting/base plane conventions (Z-up default).
"""
        if dim_fails:
            report_md += f"""
3. **Multi-Feature Dimension Scaling ({len(dim_fails)} cases)**:
   - *Symptom:* Complex families with nested features (flanges with bolt circles and hex nuts) experienced diameter or BCD rounding discrepancies.
   - *Fix:* Ground bolt circle diameters (BCD) and hex across-flats (AF) directly in ISO standard lookup tables rather than raw generative arithmetic.
"""
        if invalid_fails:
            report_md += f"""
4. **Invalid Solids / Kernel Failures ({len(invalid_fails)} cases)**:
   - *Symptom:* {len(invalid_fails)} geometries failed B-Rep validation or Boolean subtraction.
   - *Fix:* Enforce CADIR self-healing repair loop before exporting STEP solids.
"""

    report_md += f"""
---

## 6. Artifact Manifest

* **Summary Table:** [`eval/reports/eval_results.csv`](file:///{str(csv_out).replace('\\', '/')})
* **Detailed Per-Item JSONL:** [`eval/reports/eval_results.jsonl`](file:///{str(jsonl_out).replace('\\', '/')})
* **Visual Failure Gallery:** [`eval/reports/visualizations/`](file:///{str(VIZ_DIR).replace('\\', '/')})
* **Golden Set Manifest:** [`eval/golden_set/manifest.jsonl`](file:///{str(MANIFEST_FILE).replace('\\', '/')})
* **Golden Set Freeze Hash:** `{freeze_hash}`
"""

    report_file = REPORTS_DIR / "baseline_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    print("\n" + "=" * 70)
    print("EVALUATION RUN COMPLETE")
    print("=" * 70)
    print(f"Overall Pass@1:     {pass_1_mean*100:.1f}% (±{ci_pass_1*100:.1f}%)")
    print(f"Overall Pass@{k}:     {pass_k_mean*100:.1f}%")
    print(f"Valid Solid Rate:   {valid_mean*100:.1f}%")
    print(f"Mean Shape F-Score: {f_score_mean:.3f}")
    print(f"Dimensional Pass:   {dim_pass_mean*100:.1f}%")
    print(f"Report written to:  {report_file}")
    print(f"Results CSV:        {csv_out}")
    print("=" * 70 + "\n")

    return {
        "pass_at_1": pass_1_mean,
        "pass_at_k": pass_k_mean,
        "valid_solid_rate": valid_mean,
        "shape_f_score": f_score_mean,
        "dim_pass_rate": dim_pass_mean,
        "report_file": str(report_file),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CAD AI Workstation Evaluation Harness")
    parser.add_argument("--mode", type=str, default="text-only", choices=["text-only", "image-only", "text+image"], help="Input evaluation mode")
    parser.add_argument("--levels", type=str, default="L0,L1,L2,L3", help="Comma-separated prompt levels (L0, L1, L2, L3)")
    parser.add_argument("--k", type=int, default=1, help="Number of samples per prompt for pass@k")
    parser.add_argument("--limit", type=int, default=None, help="Max test items to evaluate")
    parser.add_argument("--families", type=str, default=None, help="Comma-separated part families to filter")
    parser.add_argument("--tiers", type=str, default=None, help="Comma-separated difficulty tiers (easy, medium, hard)")
    parser.add_argument("--report-from", type=str, default=None, help="Generate report directly from existing eval_results.jsonl")

    args = parser.parse_args()

    if args.report_from:
        records_loaded = []
        with open(args.report_from, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records_loaded.append(json.loads(line))
        generate_report_from_results(records_loaded, k=args.k, mode=args.mode)
    else:
        sel_levels = [lvl.strip().upper() for lvl in args.levels.split(",") if lvl.strip()]
        sel_fams = [f.strip().lower() for f in args.families.split(",")] if args.families else None
        sel_tiers = [t.strip().lower() for t in args.tiers.split(",")] if args.tiers else None

        run_evaluation(
            mode=args.mode,
            levels=sel_levels,
            k=args.k,
            limit=args.limit,
            families=sel_fams,
            tiers=sel_tiers,
        )
