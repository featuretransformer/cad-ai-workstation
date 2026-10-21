"""
Comprehensive Automated Evaluator for the User's 100 Mechanical CAD Test Prompts.
Loads prompts from parsed_user_prompts.json (originating from c:\\Users\\shiva\\OneDrive\\Desktop\\cad-ai-workstation-main\\test).
Executes each prompt through cad_graph, tracks full physical/geometric telemetry,
scores each prompt across the 7 suggested criteria (0-5 scale), and produces
a detailed JSON and Markdown report.
"""
import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.graph import cad_graph
from agents.state import AgentState

PROMPTS_FILE = backend_dir / "scripts" / "parsed_user_prompts.json"
RESULTS_JSON = backend_dir / "exports" / "user_100_prompts_evaluation.json"


def evaluate_single_prompt(item: Dict[str, Any]) -> Dict[str, Any]:
    """Execute pipeline for a single prompt and compute 7-dimension scores."""
    pid = item["id"]
    name = item["name"]
    tier = item["tier"]
    level = item["level"]
    prompt = item["prompt"]

    t0 = time.time()
    initial_state: AgentState = {
        "design_id": f"eval_{pid.lower()}",
        "session_id": "sess_eval_user100",
        "user_prompt": prompt,
        "max_retries": 3,
        "parsed_intent": {},
        "cad_code": "",
        "cad_script_history": [],
        "execution_result": {},
        "feature_tree": {},
        "export_paths": {},
        "geometry_valid": False,
        "validation_errors": [],
        "validation_stats": {},
        "dfm_report": {},
        "engineering_report": {},
        "cost_estimate": {},
        "safety_report": {},
        "cam_report": {},
        "doc_report": {},
        "alternatives": [],
        "confidence_scores": {},
        "error_count": 0,
        "last_error": "",
        "messages": [],
    }

    try:
        final_state = cad_graph.invoke(initial_state)
        latency = round(time.time() - t0, 3)

        is_assembly = final_state.get("is_assembly", False)
        cadir_valid = final_state.get("cadir_valid", False) or (is_assembly and bool(final_state.get("component_cadirs")))
        geometry_valid = final_state.get("geometry_valid", False)
        exec_res = final_state.get("execution_result", {})
        volume = exec_res.get("volume", 0.0)
        bbox = exec_res.get("bounding_box", {})
        solid_count = exec_res.get("solids_count", 1 if volume > 0 else 0)

        export_paths = final_state.get("export_paths", {})
        has_step = bool(export_paths.get("step") and Path(export_paths["step"]).exists())
        has_stl = bool(export_paths.get("stl") and Path(export_paths["stl"]).exists())
        has_glb = bool(export_paths.get("glb") and Path(export_paths["glb"]).exists())
        has_py = bool(export_paths.get("python") and Path(export_paths["python"]).exists())
        has_drawing = bool(export_paths.get("drawing") and Path(export_paths["drawing"]).exists())

        asm_obj = final_state.get("assembly_spec")
        comp_count = 1
        comp_names = []
        if is_assembly and asm_obj is not None:
            if hasattr(asm_obj, "components"):
                comp_count = len(asm_obj.components)
                comp_names = [c.name for c in asm_obj.components]
            elif isinstance(asm_obj, dict):
                comp_count = len(asm_obj.get("components", []))
                comp_names = [c.get("name", "") for c in asm_obj.get("components", [])]

        asm_val = final_state.get("assembly_validation", {})
        interf_vol = asm_val.get("total_interference_volume", 0.0) if is_assembly else 0.0
        clearance_ok = asm_val.get("clearance_check_passed", True) if is_assembly else True

        # Genuine Engineering Fidelity Scoring
        fidelity_score = 5
        cad_code_str = final_state.get("cad_code", "").lower()
        prompt_lower = prompt.lower()

        if is_assembly:
            comp_str = " ".join(comp_names).lower()
            if ("finger" in comp_str or "gripper" in comp_str) and "gripper" not in name.lower() and "finger" not in name.lower():
                fidelity_score = 1
            elif comp_count < 2:
                fidelity_score = 2
        else:
            dx = round(bbox.get("xmax", 0) - bbox.get("xmin", 0), 1)
            dy = round(bbox.get("ymax", 0) - bbox.get("ymin", 0), 1)
            dz = round(bbox.get("zmax", 0) - bbox.get("zmin", 0), 1)
            box_dims = sorted([dx, dy, dz])
            if box_dims == [12.0, 40.0, 60.0] and "60" not in prompt and "40" not in prompt:
                fidelity_score = 2
            elif "nut" in prompt_lower and "hex" in prompt_lower and "regularpolygon" not in cad_code_str:
                fidelity_score = 2
            elif "channel" in prompt_lower and volume > 100000:
                fidelity_score = 2

        # Success determination: Requires geometry, exports, and valid fidelity
        success = (cadir_valid and geometry_valid and (has_step or has_stl) and volume > 0 and fidelity_score >= 3)
        if is_assembly and interf_vol > 0.01:
            success = False

        # Compute 7-dimension scores (0 to 5 each)
        exec_score = 5 if success else (3 if cadir_valid else 1)
        geom_score = 5 if (geometry_valid and volume > 0) else 0
        dim_score = 5 if (geometry_valid and volume > 0 and bbox) else 1
        topo_score = 5 if (solid_count >= 1 and (not is_assembly or solid_count >= 2)) else 3
        asm_score = 5 if (not is_assembly or (clearance_ok and interf_vol < 0.01 and comp_count >= 2)) else 2
        export_score = 5 if (has_step and has_stl and has_glb and has_py and has_drawing) else (4 if (has_step and has_stl and has_glb) else (3 if has_step or has_stl else 0))

        total_score = exec_score + geom_score + dim_score + topo_score + export_score + fidelity_score
        max_possible = 30
        if is_assembly:
            total_score += asm_score
            max_possible = 35

        score_pct = round((total_score / max_possible) * 100.0, 1)

        return {
            "id": pid,
            "name": name,
            "tier": tier,
            "level": level,
            "prompt": prompt,
            "is_assembly": is_assembly,
            "component_count": comp_count,
            "component_names": comp_names,
            "solid_count": solid_count,
            "cadir_valid": cadir_valid,
            "geometry_valid": geometry_valid,
            "volume_mm3": round(volume, 2),
            "bounding_box": bbox,
            "interference_volume_mm3": round(interf_vol, 4),
            "clearance_pass": clearance_ok,
            "has_step": has_step,
            "has_stl": has_stl,
            "has_glb": has_glb,
            "has_py": has_py,
            "has_drawing": has_drawing,
            "latency_sec": latency,
            "scores": {
                "execution": exec_score,
                "geometry": geom_score,
                "dimensions": dim_score,
                "topology": topo_score,
                "assembly": asm_score if is_assembly else "N/A",
                "export": export_score,
                "fidelity": fidelity_score,
                "total": total_score,
                "max": max_possible,
                "percentage": score_pct,
            },
            "success": success,
            "error": final_state.get("last_error", ""),
        }
    except Exception as e:
        latency = round(time.time() - t0, 3)
        return {
            "id": pid,
            "name": name,
            "tier": tier,
            "level": level,
            "prompt": prompt,
            "is_assembly": False,
            "component_count": 0,
            "solid_count": 0,
            "cadir_valid": False,
            "geometry_valid": False,
            "volume_mm3": 0.0,
            "bounding_box": {},
            "interference_volume_mm3": 0.0,
            "clearance_pass": False,
            "has_step": False,
            "has_stl": False,
            "has_glb": False,
            "latency_sec": latency,
            "scores": {
                "execution": 0,
                "geometry": 0,
                "dimensions": 0,
                "topology": 0,
                "assembly": 0,
                "export": 0,
                "fidelity": 0,
                "total": 0,
                "max": 30,
                "percentage": 0.0,
            },
            "success": False,
            "error": str(e),
        }


def main():
    if not PROMPTS_FILE.exists():
        print(f"Error: {PROMPTS_FILE} not found!")
        return

    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        prompts: List[Dict[str, Any]] = json.load(f)

    print("=" * 80)
    print("AI-NATIVE CAD-CAM WORKSTATION: BENCHMARK ON USER'S 100 PROMPTS")
    print(f"Evaluating: {len(prompts)} prompts from {PROMPTS_FILE.name}")
    print("=" * 80)

    results: List[Dict[str, Any]] = []
    start_time = time.time()

    for i, item in enumerate(prompts, 1):
        pid = item["id"]
        pname = item["name"]
        tier = item["tier"]
        print(f"[{i:03d}/100] ({tier}) {pid}: {pname} ... ", end="", flush=True)
        res = evaluate_single_prompt(item)
        status = "PASS" if res["success"] else "FAIL"
        vol = res["volume_mm3"]
        sec = res["latency_sec"]
        score_pct = res["scores"]["percentage"]
        print(f"{status} | Vol: {vol} mm3 | Score: {score_pct}% | {sec}s")
        results.append(res)

    total_time = round(time.time() - start_time, 2)

    # Aggregations
    total_passed = sum(1 for r in results if r["success"])
    overall_pass_rate = round((total_passed / len(results)) * 100.0, 1)

    l1_results = [r for r in results if r["id"].startswith("E")]
    l2_results = [r for r in results if r["id"].startswith("M")]
    l3_results = [r for r in results if r["id"].startswith("C")]
    l4_results = [r for r in results if r["id"].startswith("H")]

    l1_pass = sum(1 for r in l1_results if r["success"])
    l2_pass = sum(1 for r in l2_results if r["success"])
    l3_pass = sum(1 for r in l3_results if r["success"])
    l4_pass = sum(1 for r in l4_results if r["success"])

    avg_latency = round(sum(r["latency_sec"] for r in results) / len(results), 2)
    step_count = sum(1 for r in results if r["has_step"])
    stl_count = sum(1 for r in results if r["has_stl"])
    glb_count = sum(1 for r in results if r["has_glb"])
    py_count = sum(1 for r in results if r.get("has_py"))
    drawing_count = sum(1 for r in results if r.get("has_drawing"))

    asm_results = [r for r in results if r.get("is_assembly")]
    total_components = sum(r.get("component_count", 1) for r in results)
    avg_components_asm = round(sum(r.get("component_count", 1) for r in asm_results) / max(len(asm_results), 1), 1)

    overall_avg_score = round(sum(r["scores"]["percentage"] for r in results) / len(results), 1)

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_prompts": len(results),
        "total_passed": total_passed,
        "total_failed": len(results) - total_passed,
        "overall_success_rate": overall_pass_rate,
        "overall_average_score_pct": overall_avg_score,
        "total_execution_time_seconds": total_time,
        "average_latency_seconds": avg_latency,
        "complexity_metrics": {
            "total_assemblies": len(asm_results),
            "total_components": total_components,
            "average_components_per_assembly": avg_components_asm,
        },
        "exports": {
            "step_count": step_count,
            "stl_count": stl_count,
            "glb_count": glb_count,
            "py_count": py_count,
            "drawing_count": drawing_count,
        },
        "levels": {
            "level_1_easy": {
                "total": len(l1_results),
                "passed": l1_pass,
                "rate": round((l1_pass / len(l1_results)) * 100.0, 1),
                "avg_score_pct": round(sum(r["scores"]["percentage"] for r in l1_results) / len(l1_results), 1),
            },
            "level_2_medium": {
                "total": len(l2_results),
                "passed": l2_pass,
                "rate": round((l2_pass / len(l2_results)) * 100.0, 1),
                "avg_score_pct": round(sum(r["scores"]["percentage"] for r in l2_results) / len(l2_results), 1),
            },
            "level_3_complex": {
                "total": len(l3_results),
                "passed": l3_pass,
                "rate": round((l3_pass / len(l3_results)) * 100.0, 1),
                "avg_score_pct": round(sum(r["scores"]["percentage"] for r in l3_results) / len(l3_results), 1),
            },
            "level_4_highly_complex": {
                "total": len(l4_results),
                "passed": l4_pass,
                "rate": round((l4_pass / len(l4_results)) * 100.0, 1),
                "avg_score_pct": round(sum(r["scores"]["percentage"] for r in l4_results) / len(l4_results), 1),
            },
        },
    }

    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print("\n" + "=" * 80)
    print("USER 100 PROMPTS BENCHMARK COMPLETE")
    print(f"Overall Success Rate: {overall_pass_rate}% ({total_passed}/{len(results)})")
    print(f"Overall Quality Score: {overall_avg_score}%")
    print(f"  - Level 1 (Easy 20):            {summary['levels']['level_1_easy']['rate']}% (Avg Score: {summary['levels']['level_1_easy']['avg_score_pct']}%)")
    print(f"  - Level 2 (Medium 30):          {summary['levels']['level_2_medium']['rate']}% (Avg Score: {summary['levels']['level_2_medium']['avg_score_pct']}%)")
    print(f"  - Level 3 (Complex 30):         {summary['levels']['level_3_complex']['rate']}% (Avg Score: {summary['levels']['level_3_complex']['avg_score_pct']}%)")
    print(f"  - Level 4 (Highly Complex 20):  {summary['levels']['level_4_highly_complex']['rate']}% (Avg Score: {summary['levels']['level_4_highly_complex']['avg_score_pct']}%)")
    print(f"Exports: STEP: {step_count}/100 | STL: {stl_count}/100 | GLB: {glb_count}/100 | PY: {py_count}/100 | 2D Drawing: {drawing_count}/100")
    print(f"Assemblies: {len(asm_results)} | Total Components: {total_components} | Avg Components/Assembly: {avg_components_asm}")
    print(f"Total Time: {total_time}s | Avg Latency: {avg_latency}s/model")
    print(f"Saved: {RESULTS_JSON}")
    print("=" * 80)


if __name__ == "__main__":
    main()
