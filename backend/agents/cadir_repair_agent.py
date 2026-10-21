"""
CADIR Repair Agent Node.
Performs self-healing on failing CADIR models using failure classification,
knowledge retrieval, and parametric adjustments.
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
    Diagnoses and repairs failures in CADIR document, code generation, or geometry execution.
    """
    doc = state.get("cadir_document")
    attempts = state.get("repair_attempts", 0) + 1
    error_count = state.get("error_count", 0) + 1

    # Extract all error messages
    error_msg = state.get("last_error") or state.get("execution_error") or ""
    exec_res_error = (state.get("execution_result") or {}).get("error") or ""
    cadir_errors = state.get("cadir_errors") or []
    val_errors = state.get("validation_errors") or []
    val_warnings = state.get("validation_warnings") or []

    all_error_text = f"{error_msg} {exec_res_error} {' '.join(cadir_errors)} {' '.join(val_errors)} {' '.join(val_warnings)}".lower()

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

    # 0. Empty Mesh / Zero Volume Repair (cut swallowed solid body)
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

    # 1. Fillet Repair: Reduce radius if too large or remove failed fillet
    elif "fillet" in all_error_text:
        for f in repaired_doc.features:
            if f.feature_type == "fillet":
                if f.radius and f.radius > 0.5:
                    f.radius = round(f.radius * 0.5, 2)
                else:
                    f.suppressed = True

    # 2. Chamfer Repair: Reduce distance
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
                if f.depth is None or f.depth <= 0:
                    f.depth = base_h + 5.0
                if f.diameter and f.diameter > (max_half_x * 1.5):
                    f.diameter = round(max_half_x * 0.8, 2)
                    f.radius = f.diameter / 2.0
                # Clamp position coordinates within host body
                if f.position:
                    r = f.radius or (f.diameter / 2.0 if f.diameter else 3.3)
                    margin = max(4.0, r * 1.5)
                    if abs(f.position.x) >= max_half_x:
                        f.position.x = (max_half_x - margin) if f.position.x > 0 else (-max_half_x + margin)
                    if abs(f.position.y) >= max_half_y:
                        f.position.y = (max_half_y - margin) if f.position.y > 0 else (-max_half_y + margin)

    # 4. Cylinder / Box Missing Height or Radius Repair
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

    # 4. Dependency Repair
    elif "dependency" in all_error_text or "cycle" in all_error_text:
        prev_id = None
        for f in repaired_doc.features:
            f.dependencies = [prev_id] if prev_id else []
            prev_id = f.id

    # 5. General Fallback: Ensure dimensions are strictly positive
    else:
        for f in repaired_doc.features:
            if f.distance is not None and f.distance <= 0:
                f.distance = 10.0
            if f.length is not None and f.length <= 0:
                f.length = 10.0

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
