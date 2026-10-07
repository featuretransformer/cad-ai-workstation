"""
Validation, Interpretation, and Execution Nodes for the LangGraph CAD Pipeline.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from cad.cadir.validator import validate_cadir_document
from cad.cadir.interpreter import generate_build123d_code
from cad.executor import execute_cad_code
from cad.validator import validate_step, validate_mesh
from cad.exporter import generate_all_exports
from cad.feature_tree import extract_features_from_code, build_tree


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
    Executes compiled build123d code in a sandboxed subprocess, generates exports, and extracts feature tree.
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
        export_paths = generate_all_exports(design_id, res["step_path"], res["stl_path"])

    conf = {**state.get("confidence_scores", {})}
    conf["cad_executor"] = 1.0 if success else 0.0

    return {
        "execution_result": res,
        "feature_tree": ftree,
        "export_paths": export_paths,
        "last_error": res.get("error", "") if not success else "",
        "confidence_scores": conf,
        "current_agent": "cad_executor",
    }


def geometry_validator_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates physical geometry: watertightness, volume, non-manifold checks via trimesh.
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
            "confidence_scores": conf,
            "current_agent": "geometry_validator",
        }

    export_paths = state.get("export_paths", {})
    step_path = export_paths.get("step") or exec_res.get("step_path")
    stl_path = export_paths.get("stl") or exec_res.get("stl_path")

    val_errors = []
    val_warnings = []
    stats = {}

    if step_path:
        step_res = validate_step(step_path)
        val_errors.extend(step_res.get("errors", []))
        val_warnings.extend(step_res.get("warnings", []))

    if stl_path:
        mesh_res = validate_mesh(stl_path)
        val_errors.extend(mesh_res.get("errors", []))
        val_warnings.extend(mesh_res.get("warnings", []))
        stats = mesh_res.get("stats", {})

    is_valid = len(val_errors) == 0

    conf = {**state.get("confidence_scores", {})}
    conf["geometry_validator"] = 0.95 if is_valid else 0.2

    return {
        "geometry_valid": is_valid,
        "validation_errors": val_errors,
        "validation_stats": stats,
        "confidence_scores": conf,
        "current_agent": "geometry_validator",
    }
