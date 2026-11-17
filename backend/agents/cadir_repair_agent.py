"""
CADIR Repair Agent Node.
Performs self-healing on failing CADIR models using failure classification,
knowledge retrieval, parametric adjustments, SoM visual critic feedback (Upgrade 5),
and localized in-place AST diffing (Upgrade P0.4).
"""
from typing import Dict, Any, Optional
from pathlib import Path
import copy
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from cad.cadir.schema import CADIRDocument
from retrieval.index import KnowledgeIndex
from retrieval.query import search_knowledge_base, CADIRQuery
from config import settings


def cadir_repair_node(state: AgentState) -> Dict[str, Any]:
    """
    Diagnoses and repairs failures in CADIR document, code generation, geometry execution,
    or visual alignment from the SoM Visual Critic Node using localized AST diffing (P0.4).
    """
    doc = state.get("cadir_document")
    attempts = state.get("repair_attempts", 0) + 1
    error_count = state.get("error_count", 0) + 1

    # Extract error messages & judge decisions
    judge_dec = state.get("judge_decision") or {}
    targeted_feat_id = judge_dec.get("targeted_feature_id")
    suggested_patch = judge_dec.get("suggested_patch") or {}
    failure_targets = judge_dec.get("failure_targets") or []

    error_msg = state.get("last_error") or state.get("execution_error") or ""
    exec_res_error = (state.get("execution_result") or {}).get("error") or ""
    cadir_errors = state.get("cadir_errors") or []
    val_errors = state.get("validation_errors") or []
    val_warnings = state.get("validation_warnings") or []

    # Visual critique feedback (Upgrade 5)
    visual_critique = state.get("visual_critique") or {}
    visual_instruction = visual_critique.get("spatial_correction_instruction", "")
    if not targeted_feat_id:
        targeted_feat_id = visual_critique.get("faulty_feature_id")

    all_error_text = f"{error_msg} {exec_res_error} {' '.join(cadir_errors)} {' '.join(val_errors)} {' '.join(val_warnings)} {visual_instruction}".lower()

    conf = {**state.get("confidence_scores", {})}
    conf["cadir_repair"] = 0.85

    if doc is None:
        return {
            "repair_attempts": attempts,
            "error_count": error_count,
            "confidence_scores": conf,
            "current_agent": "cadir_repair",
        }

    repaired_doc = copy.deepcopy(doc)
    repaired_in_place = False

    # ──────────────────────────────────────────────────────────────────────────
    # P0.4: LOCALIZED IN-PLACE AST DIFF REPAIR
    # If a specific faulty feature is targeted by QA Judge or Visual Verifier,
    # patch ONLY that feature node and leave all sibling features intact.
    # ──────────────────────────────────────────────────────────────────────────
    if targeted_feat_id and repaired_doc.features:
        target_f = next((f for f in repaired_doc.features if f.id == targeted_feat_id or targeted_feat_id in f.id), None)
        if target_f:
            # 1. Visual critique spatial orientation patch
            if visual_instruction and not visual_critique.get("visually_aligned", True):
                if "top" in visual_instruction.lower():
                    target_f.target_face_selector = "top"
                elif "bottom" in visual_instruction.lower():
                    target_f.target_face_selector = "bottom"
                elif "front" in visual_instruction.lower():
                    target_f.target_face_selector = "front"
                elif "reverse" in visual_instruction.lower() or "flip" in visual_instruction.lower():
                    target_f.target_face_selector = "bottom" if target_f.target_face_selector == "top" else "top"
                if "cut" in visual_instruction.lower() and target_f.operation != "cut":
                    target_f.operation = "cut"
                repaired_in_place = True

            # 2. Target dimensional discrepancy patch
            t_id = suggested_patch.get("target_id", "")
            t_kind = suggested_patch.get("target_kind", "")
            nom_val = suggested_patch.get("nominal")

            if nom_val is not None:
                if "overall-x" in t_id and target_f.length is not None:
                    target_f.length = float(nom_val)
                    repaired_in_place = True
                elif "overall-y" in t_id and target_f.width is not None:
                    target_f.width = float(nom_val)
                    repaired_in_place = True
                elif "overall-z" in t_id and target_f.height is not None:
                    target_f.height = float(nom_val)
                    repaired_in_place = True
                elif ("bore" in t_id or "hole" in t_id or t_kind == "hole_diameter") and target_f.feature_type in ("hole", "counterbore", "cylinder"):
                    target_f.diameter = float(nom_val)
                    target_f.radius = float(nom_val) / 2.0
                    target_f.operation = "cut"
                    repaired_in_place = True
                elif ("pcd" in t_id or t_kind == "bolt_circle"):
                    if target_f.position:
                        target_f.position.x = float(nom_val) / 2.0
                    repaired_in_place = True

            # 3. Fillet / Chamfer localized repair
            if target_f.feature_type == "fillet":
                if target_f.radius and target_f.radius > 0.5:
                    target_f.radius = max(0.5, round(target_f.radius * 0.5, 2))
                else:
                    target_f.suppressed = True
                repaired_in_place = True
            elif target_f.feature_type == "chamfer":
                if target_f.distance and target_f.distance > 0.2:
                    target_f.distance = max(0.2, round(target_f.distance * 0.5, 2))
                    target_f.length = target_f.distance
                else:
                    target_f.suppressed = True
                repaired_in_place = True

            # 4. Cut missing solid body (NullBooleanCut)
            if target_f.operation == "cut" and ("volume-delta" in all_error_text or "empty" in all_error_text):
                base_b = repaired_doc.features[0]
                target_f.depth = (base_b.height or 20.0) + 5.0
                target_f.target_face_selector = "top"
                repaired_in_place = True

    # ──────────────────────────────────────────────────────────────────────────
    # FALLBACK REPAIRS (When no specific feature is isolated or in-place was skipped)
    # ──────────────────────────────────────────────────────────────────────────
    if not repaired_in_place:
        # Visual Critique Fallback
        if visual_instruction and not visual_critique.get("visually_aligned", True):
            for f in repaired_doc.features:
                if f.feature_type in ("hole", "pocket", "counterbore") and not f.target_face_selector:
                    f.target_face_selector = "top"

        # 0. Empty Mesh / Zero Volume Repair
        if "empty" in all_error_text or "volume" in all_error_text or "mesh" in all_error_text:
            for f in repaired_doc.features:
                if f.feature_type in ("hole", "pocket"):
                    deps = f.dependencies or []
                    parent = next((pf for pf in repaired_doc.features if pf.id in deps), None)
                    if not parent and repaired_doc.features:
                        parent = repaired_doc.features[0]
                    if parent and parent.feature_type in ("cylinder", "sphere") and parent.radius:
                        f.radius = round(parent.radius * 0.5, 2)
                        f.diameter = f.radius * 2.0
                    elif parent and parent.feature_type == "box" and parent.length and parent.width:
                        max_r = min(parent.length, parent.width) / 2.0
                        f.radius = round(max_r * 0.5, 2)
                        f.diameter = f.radius * 2.0
                elif f.feature_type in ("chamfer", "fillet"):
                    if f.distance and f.distance > 0.5:
                        f.distance = 0.5
                        f.length = 0.5
                    if f.radius and f.radius > 0.5:
                        f.radius = 0.5

        # 1. Fillet Repair
        elif "fillet" in all_error_text:
            for f in repaired_doc.features:
                if f.feature_type == "fillet":
                    if f.radius and f.radius > 0.5:
                        f.radius = round(f.radius * 0.5, 2)
                    else:
                        f.suppressed = True

        # 2. Chamfer Repair
        elif "chamfer" in all_error_text:
            for f in repaired_doc.features:
                if f.feature_type == "chamfer":
                    if f.distance and f.distance > 0.2:
                        f.distance = round(f.distance * 0.5, 2)
                        f.length = f.distance
                    else:
                        f.suppressed = True

        # 3. Hole Depth / Radius / Position / Operation Repair
        elif "hole" in all_error_text or "bore" in all_error_text or "position" in all_error_text or "bounds" in all_error_text:
            base_body = repaired_doc.features[0] if repaired_doc.features else None
            max_half_x = (base_body.length / 2.0) if base_body and base_body.length else 50.0
            max_half_y = (base_body.width / 2.0) if base_body and base_body.width else 40.0
            base_h = (base_body.height or 20.0) if base_body else 20.0

            for f in repaired_doc.features:
                if f.feature_type == "hole":
                    f.operation = "cut"
                    if not f.target_face_selector:
                        f.target_face_selector = "top"
                    if f.depth is None or f.depth <= 0:
                        f.depth = base_h + 5.0
                    if f.diameter and f.diameter > (max_half_x * 1.5):
                        f.diameter = round(max_half_x * 0.8, 2)
                        f.radius = f.diameter / 2.0
                    if f.position:
                        r = f.radius or (f.diameter / 2.0 if f.diameter else 3.3)
                        margin = max(4.0, r * 1.5)
                        if abs(f.position.x) >= max_half_x:
                            f.position.x = (max_half_x - margin) if f.position.x > 0 else (-max_half_x + margin)
                        if abs(f.position.y) >= max_half_y:
                            f.position.y = (max_half_y - margin) if f.position.y > 0 else (-max_half_y + margin)

        # 4. Missing Cylinder / Box Height or Radius
        if "height" in all_error_text:
            for f in repaired_doc.features:
                if f.feature_type == "cylinder" and (f.height is None or f.height <= 0):
                    f.height = f.length or f.depth or 20.0
                elif f.feature_type == "box" and (f.height is None or f.height <= 0):
                    f.height = 10.0

        if "radius" in all_error_text:
            for f in repaired_doc.features:
                if f.feature_type in ("cylinder", "sphere") and (f.radius is None or f.radius <= 0):
                    f.radius = (f.diameter / 2.0) if f.diameter else 10.0

        # 5. Dependency Repair
        elif "dependency" in all_error_text or "cycle" in all_error_text:
            prev_id = None
            for f in repaired_doc.features:
                f.dependencies = [prev_id] if prev_id else []
                prev_id = f.id

        # 6. General Fallback: strictly positive dimensions
        else:
            for f in repaired_doc.features:
                if f.distance is not None and f.distance <= 0:
                    f.distance = 10.0
                if f.length is not None and f.length <= 0:
                    f.length = 10.0

        # Last-resort fallback: synthesize fresh parametric CADIR if multiple retries exhausted
        if attempts >= 3:
            try:
                from agents.design_agent import _synthesize_parametric_cadir
                d_id = state.get("design_id", "repaired_part")
                p_text = state.get("user_prompt", "")
                p_intent = state.get("parsed_intent", {})
                r_ex = state.get("retrieved_examples", [])
                syn_doc = _synthesize_parametric_cadir(d_id, p_text, p_intent, r_ex)
                if syn_doc and syn_doc.features:
                    repaired_doc = syn_doc
            except Exception:
                pass

    if hasattr(repaired_doc, "model_dump") and hasattr(doc, "model_dump"):
        if repaired_doc.model_dump() == doc.model_dump():
            attempts = state.get("max_retries", 5)
    elif repaired_doc == doc:
        attempts = state.get("max_retries", 5)

    return {
        "cadir_document": repaired_doc,
        "repair_attempts": attempts,
        "error_count": error_count,
        "cadir_errors": [],
        "validation_errors": [],
        "last_error": "",
        "geometry_valid": False,
        "confidence_scores": conf,
        "current_agent": "cadir_repair",
    }
