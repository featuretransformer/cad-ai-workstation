"""
Assembly Graph Nodes for LangGraph Workflow.
Handles multi-component assembly synthesis, build123d Compound execution,
OpenCASCADE interference & clearance validation, and state aggregation.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from cad.assembly.schema import AssemblySpec
from cad.assembly.component_generator import generate_component_cadir
from cad.assembly.executor import execute_assembly
from cad.assembly.validator import validate_assembly
from cad.feature_tree import extract_features_from_code, build_tree


def assembly_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Per-component CADIR generation loop.
    Iterates over all components in AssemblySpec, generates parametric CADIRDocuments,
    and assigns the primary/base solid to cadir_document for downstream compatibility.
    """
    asm_spec: Optional[AssemblySpec] = state.get("assembly_spec")
    if not asm_spec:
        return {
            "error_count": state.get("error_count", 0) + 1,
            "last_error": "No AssemblySpec found in assembly_generator_node.",
            "current_agent": "assembly_generator",
        }

    component_cadirs: Dict[str, Any] = {}
    primary_doc = None

    for comp in asm_spec.components:
        if comp.cadir_document is None:
            comp.cadir_document = generate_component_cadir(comp, asm_spec)

        component_cadirs[comp.component_id] = comp.cadir_document
        if primary_doc is None or comp.role in ("mounting_plate", "base_plate", "housing"):
            primary_doc = comp.cadir_document

    conf = {**state.get("confidence_scores", {})}
    conf["assembly_generator"] = 0.98

    return {
        "assembly_spec": asm_spec,
        "component_cadirs": component_cadirs,
        "cadir_document": primary_doc,  # Primary base part for downstream nodes
        "cadir_valid": True,
        "confidence_scores": conf,
        "current_agent": "assembly_generator",
    }


def assembly_executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes the multi-component assembly via build123d.
    Produces multi-body STEP, combined STL, GLB preview, per-component STLs, and feature tree.
    """
    asm_spec: Optional[AssemblySpec] = state.get("assembly_spec")
    design_id = state.get("design_id", "default_design")

    if not asm_spec:
        return {
            "execution_result": {"success": False, "error": "Missing AssemblySpec."},
            "last_error": "Missing AssemblySpec for assembly execution.",
            "current_agent": "assembly_executor",
        }

    res = execute_assembly(asm_spec, design_id)
    success = res.get("success", False)

    # Feature tree extracted from the generated assembly code
    code = res.get("cad_code", "")
    ftree = build_tree(extract_features_from_code(code)) if code else {}

    conf = {**state.get("confidence_scores", {})}
    conf["assembly_executor"] = 1.0 if success else 0.0

    return {
        "execution_result": res,
        "export_paths": res.get("export_paths", {}),
        "cad_code": code,
        "feature_tree": ftree,
        "last_error": res.get("error", "") if not success else "",
        "confidence_scores": conf,
        "current_agent": "assembly_executor",
    }


def assembly_validator_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates physical feasibility of the assembled geometry:
    Pairwise collision/interference volume, clearance margins, and dimensional envelope.
    """
    asm_spec: Optional[AssemblySpec] = state.get("assembly_spec")
    exec_res = state.get("execution_result", {})

    if not asm_spec or not exec_res.get("success", False):
        err = exec_res.get("error") or "Execution failed before assembly validation."
        conf = {**state.get("confidence_scores", {})}
        conf["assembly_validator"] = 0.0
        return {
            "geometry_valid": False,
            "validation_errors": [err],
            "assembly_validation": {"is_valid": False, "errors": [err]},
            "confidence_scores": conf,
            "current_agent": "assembly_validator",
        }

    val_report = validate_assembly(asm_spec, exec_res)
    is_valid = val_report.get("is_valid", False)

    conf = {**state.get("confidence_scores", {})}
    conf["assembly_validator"] = 0.95 if is_valid else 0.5

    return {
        "geometry_valid": is_valid,
        "validation_errors": val_report.get("errors", []),
        "validation_warnings": val_report.get("warnings", []),
        "assembly_validation": val_report,
        "validation_stats": {
            "solids_count": exec_res.get("solids_count", 0),
            "total_volume": exec_res.get("volume", 0.0),
            "collision_count": val_report.get("collision_count", 0),
            "clearances": len(val_report.get("clearances", [])),
            "envelope": val_report.get("envelope_metrics", {}),
        },
        "confidence_scores": conf,
        "current_agent": "assembly_validator",
    }
