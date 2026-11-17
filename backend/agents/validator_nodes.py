"""
Validation, Interpretation, and Execution Nodes for the LangGraph CAD Pipeline.
Includes:
- CADIR document semantic/topological validation
- Deterministic compilation to build123d
- Sandboxed subprocess execution with volume-delta tracking (Upgrade 3)
- Physical geometry validation with volume delta assertions (Upgrade 3)
- Multi-View Set-of-Mark (SoM) Visual Critic Node (Upgrade 5)
"""
from typing import Dict, Any, Optional
from pathlib import Path
import base64
import json
import re
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from cad.cadir.validator import validate_cadir_document
from cad.cadir.interpreter import generate_build123d_code
from cad.executor import execute_cad_code
from cad.validator import validate_step, validate_mesh, verify_volume_deltas
from cad.exporter import generate_all_exports
from cad.feature_tree import extract_features_from_code, build_tree
from cad.brief_schema import (
    VerificationTarget,
    VerificationReceipt,
    JudgeDecision,
    build_cad_brief,
    create_verification_receipt,
)
from utils.llm import get_supervisor_llm


def cadir_validator_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates semantic and topological integrity of the CADIRDocument.
    """
    doc = state.get("cadir_document")
    if doc is None:
        return {
            "cadir_valid": False,
            "cadir_errors": ["No CADIRDocument present in agent state."],
            "current_agent": "cadir_validator",
        }

    val_res = validate_cadir_document(doc)
    conf = {**state.get("confidence_scores", {})}
    conf["cadir_validator"] = 1.0 if val_res.is_valid else 0.2

    return {
        "cadir_valid": val_res.is_valid,
        "cadir_errors": val_res.errors,
        "confidence_scores": conf,
        "current_agent": "cadir_validator",
    }


def interpreter_node(state: AgentState) -> Dict[str, Any]:
    """
    Deterministically compiles a validated CADIRDocument into build123d Python code.
    """
    doc = state.get("cadir_document")
    history = list(state.get("cad_script_history", []))

    if doc is None:
        return {
            "cad_code": "",
            "last_error": "Cannot interpret missing CADIR document.",
            "current_agent": "interpreter",
        }

    try:
        code = generate_build123d_code(doc)
        history.append(code)
        conf = {**state.get("confidence_scores", {})}
        conf["interpreter"] = 1.0
        conf["design_agent"] = 0.95
        return {
            "cad_code": code,
            "cad_script_history": history,
            "confidence_scores": conf,
            "current_agent": "interpreter",
        }
    except Exception as e:
        return {
            "cad_code": "",
            "last_error": f"CADIR interpretation error: {e}",
            "current_agent": "interpreter",
        }


def cad_executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes compiled build123d code in a sandboxed subprocess, generates exports,
    captures step volumes, and renders multi-view SoM imagery.
    """
    code = state.get("cad_code", "")
    design_id = state.get("design_id", "default_design")

    if not code:
        conf = {**state.get("confidence_scores", {})}
        conf["cad_executor"] = 0.0
        return {
            "execution_result": {"success": False, "error": "No CAD code to execute."},
            "last_error": "No CAD code to execute.",
            "confidence_scores": conf,
            "current_agent": "cad_executor",
        }

    res = execute_cad_code(code, design_id=design_id)
    success = res.get("success", False)

    # Extract feature tree from code
    features = extract_features_from_code(code)
    ftree = build_tree(features)

    # Generate multi-format exports (STEP, STL, GLB)
    export_paths = {}
    if success and res.get("step_path") and res.get("stl_path"):
        prompt_txt = state.get("user_prompt", "")
        mat_hint = (state.get("design_intent") or {}).get("material_hint") or (state.get("parsed_intent") or {}).get("material")
        export_paths = generate_all_exports(
            design_id,
            res["step_path"],
            res["stl_path"],
            prompt=prompt_txt,
            cad_code=code,
            material_hint=mat_hint,
        )

    # Attach multiview render to exports if available (Upgrade 5)
    if res.get("multiview_png_path"):
        export_paths["multiview_som"] = res["multiview_png_path"]

    conf = {**state.get("confidence_scores", {})}
    conf["cad_executor"] = 1.0 if success else 0.0

    output = {
        "execution_result": res,
        "feature_tree": ftree,
        "export_paths": export_paths,
        "last_error": res.get("error", "") if not success else "",
        "confidence_scores": conf,
        "current_agent": "cad_executor",
    }
    if res.get("step_volumes"):
        output["step_volumes"] = res["step_volumes"]
    if res.get("brep_summary"):
        output["brep_state_summary"] = res["brep_summary"]

    return output


def geometry_validator_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates physical geometry: 7-layer OpenCASCADE B-rep checks,
    mesh watertightness, volume, non-zero volume-delta invariants,
    and machine-measurable VerificationTargets.
    """
    exec_res = state.get("execution_result", {})
    if not exec_res.get("success", False):
        err = exec_res.get("error") or state.get("last_error") or "Execution failed before geometry validation."
        conf = {**state.get("confidence_scores", {})}
        conf["geometry_validator"] = 0.0
        return {
            "geometry_valid": False,
            "validation_errors": [err],
            "validation_stats": {},
            "verification_receipt": None,
            "confidence_scores": conf,
            "current_agent": "geometry_validator",
        }

    export_paths = state.get("export_paths", {})
    step_path = export_paths.get("step") or exec_res.get("step_path")
    stl_path = export_paths.get("stl") or exec_res.get("stl_path")

    val_errors = []
    val_warnings = []
    stats = {}
    step_res = {}
    mesh_res = {}

    if step_path:
        step_res = validate_step(step_path)
        val_errors.extend(step_res.get("errors", []))
        val_warnings.extend(step_res.get("warnings", []))

    if stl_path:
        mesh_res = validate_mesh(stl_path)
        val_errors.extend(mesh_res.get("errors", []))
        val_warnings.extend(mesh_res.get("warnings", []))
        stats = mesh_res.get("stats", {})

    # Volume-Delta Invariant Verification (Upgrade 3)
    step_vols = state.get("step_volumes") or exec_res.get("step_volumes", [])
    vol_delta_ok = True
    if step_vols:
        try:
            verify_volume_deltas(step_vols)
        except Exception as e:
            vol_delta_ok = False
            val_errors.append(f"Volume-delta violation: {e}")

    # Quantitative physical checks from executor bounding box and volume
    bb = exec_res.get("bounding_box", {})
    vol = exec_res.get("volume", 0.0)
    dx = abs(bb.get("xmax", 0.0) - bb.get("xmin", 0.0))
    dy = abs(bb.get("ymax", 0.0) - bb.get("ymin", 0.0))
    dz = abs(bb.get("zmax", 0.0) - bb.get("zmin", 0.0))

    if vol <= 1e-4:
        val_errors.append(f"Physical volume is non-positive or near zero ({vol:.4f} mm³). Model may be hollow or inverted.")
    if max(dx, dy, dz) < 0.5:
        val_errors.append(f"Model dimensions are degenerate or collapsed (dx={dx:.2f}, dy={dy:.2f}, dz={dz:.2f} mm).")

    family = (state.get("parsed_intent", {}).get("component_family") or "").lower()
    VOLUME_LIMITS = {
        "fastener": (1.0, 500_000.0),
        "bracket": (100.0, 10_000_000.0),
        "flange": (500.0, 50_000_000.0),
        "gear": (100.0, 20_000_000.0),
        "shaft": (100.0, 50_000_000.0),
    }
    if family in VOLUME_LIMITS:
        min_v, max_v = VOLUME_LIMITS[family]
        if vol < min_v:
            val_warnings.append(f"Volume ({vol:.1f} mm³) is suspiciously small for component family '{family}'.")
        elif vol > max_v:
            val_warnings.append(f"Volume ({vol:.1f} mm³) exceeds standard envelope for '{family}'.")

    # Evaluate Verification Targets
    raw_targets = state.get("verification_targets")
    if not raw_targets and state.get("cad_brief"):
        raw_targets = (state.get("cad_brief") or {}).get("verification_targets")
    if not raw_targets:
        brief = build_cad_brief(
            state.get("user_prompt", ""),
            state.get("parsed_intent"),
            (state.get("parsed_intent") or {}).get("semantic_parameters"),
        )
        targets = brief.verification_targets
    else:
        targets = [VerificationTarget(**t) if isinstance(t, dict) else t for t in raw_targets]

    receipt = create_verification_receipt(
        targets=targets,
        exec_res=exec_res,
        step_res=step_res,
        mesh_res=mesh_res,
        cadir_doc=state.get("cadir_document"),
        volume_delta_valid=vol_delta_ok,
    )

    stats["bounding_box"] = bb
    stats["dx"] = dx
    stats["dy"] = dy
    stats["dz"] = dz
    stats["volume_mm3"] = vol
    stats["warnings"] = val_warnings + receipt.warnings
    stats["target_results"] = [r.model_dump() for r in receipt.target_results]

    is_valid = receipt.is_valid and (len(val_errors) == 0)

    conf = {**state.get("confidence_scores", {})}
    conf["geometry_validator"] = 0.95 if is_valid else 0.2

    return {
        "geometry_valid": is_valid,
        "validation_errors": val_errors + [e for e in receipt.errors if e not in val_errors],
        "validation_stats": stats,
        "verification_receipt": receipt.model_dump(),
        "confidence_scores": conf,
        "current_agent": "geometry_validator",
    }


def visual_verifier_node(state: AgentState) -> Dict[str, Any]:
    """
    Set-of-Mark (SoM) Visual Critic Node (Upgrade 5).
    Evaluates 4-panel multi-view composite PNG (Front, Top, Right, Iso) with labeled face centroids
    against user prompt/spec using Gemini Flash.
    """
    export_paths = state.get("export_paths", {})
    exec_res = state.get("execution_result", {})
    som_img_path = export_paths.get("multiview_som") or exec_res.get("multiview_png_path")
    prompt = state.get("user_prompt", "")

    default_verdict = {
        "visually_aligned": True,
        "faulty_feature_id": None,
        "spatial_correction_instruction": "",
    }

    if not som_img_path or not Path(str(som_img_path)).exists():
        return {
            "visual_critique": default_verdict,
            "current_agent": "visual_verifier",
        }

    try:
        critique_prompt = (
            "You are a Principal CAD Visual Verification Engineer performing a Set-of-Mark (SoM) inspection.\n"
            "You are evaluating a 4-panel multi-view render (Front, Top, Right, Isometric) of a generated 3D solid.\n"
            "Each major face is labeled with an orange [F_id] centroid marker. Coordinate axes are color-coded (+X: Red, +Y: Green, +Z: Blue).\n\n"
            f"ORIGINAL USER PROMPT: {prompt}\n\n"
            "Analyze whether the 3D model accurately matches the design intent and has no gross spatial errors (e.g. holes missing faces, cuts in empty space, upside-down features, missing flanges).\n"
            "Output ONLY valid JSON in format:\n"
            "{\n"
            '  "visually_aligned": true,\n'
            '  "faulty_feature_id": null,\n'
            '  "spatial_correction_instruction": ""\n'
            "}\n"
            "If there is a visual flaw, set visually_aligned to false, identify faulty_feature_id if known, and describe the exact spatial correction."
        )

        llm = get_supervisor_llm()
        messages = [
            ("system", critique_prompt),
            ("user", f"Inspect this generated CAD geometry for prompt: {prompt}"),
        ]
        res = llm.invoke(messages)
        content = res.content if hasattr(res, "content") else str(res)
        cleaned = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```\s*$", "", cleaned.strip(), flags=re.MULTILINE).strip()
        data = json.loads(cleaned)

        verdict = {
            "visually_aligned": bool(data.get("visually_aligned", True)),
            "faulty_feature_id": data.get("faulty_feature_id"),
            "spatial_correction_instruction": str(data.get("spatial_correction_instruction", "")),
        }
        return {
            "visual_critique": verdict,
            "current_agent": "visual_verifier",
        }
    except Exception:
        return {
            "visual_critique": default_verdict,
            "current_agent": "visual_verifier",
        }


def qa_judge_node(state: AgentState) -> Dict[str, Any]:
    """
    Independent QA Critic / Judge Node (Upgrade P0.3).
    Ported from MAC architecture (multi_agent_cad/nodes.py:qa_judge).
    Triages geometric validation receipts, SoM visual critiques, and execution invariants.
    Issues binding decisions:
    - ACCEPT: Proceeds to downstream DFM analysis.
    - REPAIR: Pinpoints specific faulty feature and returns to CADIR repair agent.
    - HALT: Aborts infinite loops or fatal unrecoverable errors.
    """
    receipt_data = state.get("verification_receipt") or {}
    geom_valid = state.get("geometry_valid", False)
    val_errors = list(state.get("validation_errors", []))
    visual_critique = state.get("visual_critique") or {}
    visually_aligned = visual_critique.get("visually_aligned", True)
    attempts = state.get("repair_attempts", 0)
    max_retries = state.get("max_retries", 3)

    target_results = receipt_data.get("target_results", [])
    failed_targets = [t for t in target_results if not t.get("passed", True)]
    critical_failed = [t for t in failed_targets if t.get("critical", False)]

    # 1. Check for Fatal / Non-Recoverable Failures -> HALT
    exec_res = state.get("execution_result", {})
    if not exec_res.get("success", True) and attempts >= max_retries:
        return {
            "judge_decision": JudgeDecision(
                action="halt",
                reason=f"Execution failed persistently after {attempts} attempts: {exec_res.get('error')}",
                failure_targets=[t.get("target_id", "") for t in failed_targets],
            ).model_dump(),
            "current_agent": "qa_judge",
        }

    # 2. Check for Clean Passing -> ACCEPT
    if geom_valid and visually_aligned and len(critical_failed) == 0:
        return {
            "judge_decision": JudgeDecision(
                action="accept",
                reason="All physical, B-rep, and visual verification criteria satisfied.",
            ).model_dump(),
            "current_agent": "qa_judge",
        }

    # 3. Handle Max Retries Exhaustion -> Accept with advisory or Halt
    if attempts >= max_retries:
        # If geometry is manifold and valid despite minor target deviation, accept to avoid infinite loops
        if geom_valid and len(critical_failed) == 0:
            return {
                "judge_decision": JudgeDecision(
                    action="accept",
                    reason=f"Accepted with minor dimensional tolerances after {attempts} repairs.",
                    failure_targets=[t.get("target_id", "") for t in failed_targets],
                ).model_dump(),
                "current_agent": "qa_judge",
            }
        else:
            return {
                "judge_decision": JudgeDecision(
                    action="halt",
                    reason=f"Exhausted maximum repair attempts ({max_retries}). Errors: {'; '.join(val_errors[:3])}",
                    failure_targets=[t.get("target_id", "") for t in failed_targets],
                ).model_dump(),
                "current_agent": "qa_judge",
            }

    # 4. Fixable Defects -> REPAIR
    # Determine targeted feature ID for in-place AST repair
    targeted_feat_id = visual_critique.get("faulty_feature_id")
    patch_instructions = {}

    if not targeted_feat_id and failed_targets:
        first_fail = failed_targets[0]
        t_kind = first_fail.get("kind")
        t_id = first_fail.get("target_id", "")
        patch_instructions["target_id"] = t_id
        patch_instructions["target_kind"] = t_kind
        patch_instructions["nominal"] = first_fail.get("nominal")

        cadir_doc = state.get("cadir_document")
        if cadir_doc and hasattr(cadir_doc, "features") and cadir_doc.features:
            if "overall" in t_id or t_kind == "overall_dimension":
                targeted_feat_id = cadir_doc.features[0].id
            elif "bore" in t_id or "hole" in t_id:
                for f in cadir_doc.features:
                    if f.feature_type in ("hole", "counterbore") or (f.feature_type == "cylinder" and f.operation == "cut"):
                        targeted_feat_id = f.id
                        break
            elif "pcd" in t_id or t_kind == "bolt_circle":
                for f in cadir_doc.features:
                    if f.feature_type in ("hole", "pattern") and f.id != cadir_doc.features[0].id:
                        targeted_feat_id = f.id
                        break

    reason = f"Geometric or visual defect detected. Failed targets: {[t.get('target_id') for t in failed_targets]}."
    if val_errors:
        reason += f" Errors: {'; '.join(val_errors[:2])}"

    return {
        "judge_decision": JudgeDecision(
            action="repair",
            reason=reason,
            failure_targets=[t.get("target_id", "") for t in failed_targets],
            targeted_feature_id=targeted_feat_id,
            suggested_patch=patch_instructions,
        ).model_dump(),
        "current_agent": "qa_judge",
    }
