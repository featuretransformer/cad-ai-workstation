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

    # 1. Fillet Repair: Reduce radius if too large or remove failed fillet
    if "fillet" in all_error_text:
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

    # 3. Hole Depth / Radius / Position Repair
    elif "hole" in all_error_text or "bore" in all_error_text:
        for f in repaired_doc.features:
            if f.feature_type == "hole":
                if f.depth is None or f.depth <= 0:
                    f.depth = 20.0
                if f.diameter and f.diameter > 50.0:
                    f.diameter = round(f.diameter * 0.7, 2)

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
