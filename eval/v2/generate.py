"""
Generation adapters for the V2 benchmark.

Each adapter turns ``(prompt, level, part id)`` into a candidate CAD model and
returns a uniform dictionary consumed by :mod:`eval.v2.metrics`.

Two adapters are provided:

``pipeline``
    The production LangGraph workflow, exactly as a user would trigger it
    (classifier -> supervisor -> planner -> design/incremental agent -> CADIR
    validator -> interpreter -> sandboxed executor -> geometry validator ->
    downstream engineering reports).  This is the honest "what does the product
    actually output today" baseline.

``core``
    The same front half of the graph but stopping at the geometry validator.
    The downstream DFM/cost/safety/CAM/doc agents cannot change the geometry and
    only add latency, so this shaves several LLM calls per case during
    iteration.  Results are geometrically identical to ``pipeline``.
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# NOTE: no os.chdir here - the CAD executor resolves its export directory
# relative to backend/cad/executor.py, so the process cwd is irrelevant and a
# global chdir would break relative CLI paths for the runner.


def _state_for(prompt: str, design_id: str, image_path: Optional[str], input_mode: str) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "design_id": design_id,
        "max_retries": 2,
    }
    if input_mode == "image-only":
        state["user_prompt"] = "Reconstruct the mechanical CAD model shown in this isometric engineering render."
        state["file_path"] = image_path
        state["input_type"] = "image"
    elif input_mode == "text+image":
        state["user_prompt"] = prompt
        state["file_path"] = image_path
        state["input_type"] = "multimodal"
    else:
        state["user_prompt"] = prompt
        state["input_type"] = "text"
    return state


def _summarise(final: Dict[str, Any], started: float, design_id: str) -> Dict[str, Any]:
    doc = final.get("cadir_document")
    exec_res = final.get("execution_result") or {}
    export_paths = final.get("export_paths") or {}

    step_path = export_paths.get("step") or exec_res.get("step_path")
    stl_path = export_paths.get("stl") or exec_res.get("stl_path")

    def _ok(p):
        return bool(p and Path(p).exists() and Path(p).stat().st_size > 50)

    success = bool(final.get("geometry_valid", False)) and _ok(step_path) and _ok(stl_path)
    err = ""
    if not success:
        errs = final.get("validation_errors") or []
        err = "; ".join(str(e) for e in errs)[:500] or str(final.get("last_error", ""))[:500]

    features = []
    if doc is not None:
        try:
            features = [f.feature_type for f in doc.features]
        except Exception:
            features = []

    return {
        "success": success,
        "step_path": step_path if _ok(step_path) else None,
        "stl_path": stl_path if _ok(stl_path) else None,
        "error": err,
        "latency_sec": round(time.time() - started, 2),
        "cadir_features": features,
        "cadir_feature_count": len(features),
        "cadir_name": getattr(doc, "name", None),
        "component_family": getattr(doc, "component_family", None),
        "cad_lines": len((final.get("cad_code") or "").splitlines()),
        "design_id": design_id,
        "is_complex_part": final.get("is_complex_part"),
        "is_assembly": final.get("is_assembly"),
        "repair_attempts": final.get("repair_attempts"),
    }


def generate_pipeline(
    prompt: str,
    design_id: str,
    image_path: Optional[str] = None,
    input_mode: str = "text-only",
    **_ignored,
) -> Dict[str, Any]:
    """Runs the full production LangGraph workflow."""
    from agents.graph import cad_graph

    started = time.time()
    try:
        final = cad_graph.invoke(_state_for(prompt, design_id, image_path, input_mode))
        return _summarise(final, started, design_id)
    except Exception as e:
        return {
            "success": False,
            "step_path": None,
            "stl_path": None,
            "error": f"pipeline exception: {type(e).__name__}: {e}",
            "latency_sec": round(time.time() - started, 2),
            "cadir_features": [],
            "cadir_feature_count": 0,
            "design_id": design_id,
            "traceback": traceback.format_exc()[-1500:],
        }


_CORE_GRAPH = None


def _core_graph():
    """Compiles the geometry-producing prefix of the workflow (no downstream agents)."""
    global _CORE_GRAPH
    if _CORE_GRAPH is not None:
        return _CORE_GRAPH

    from langgraph.graph import StateGraph, END
    from agents.state import AgentState
    from agents.input_classifier import classify_input_node
    from agents.supervisor import supervisor_node
    from agents.design_planner import design_planner_node
    from agents.complexity_classifier import complexity_classifier_node
    from agents.feature_planner import feature_planner_node
    from agents.incremental_design_agent import incremental_design_agent_node
    from agents.design_agent import design_agent_node
    from agents.assembly_nodes import (
        assembly_generator_node,
        assembly_executor_node,
        assembly_validator_node,
    )
    from agents.validator_nodes import (
        cadir_validator_node,
        interpreter_node,
        cad_executor_node,
        geometry_validator_node,
    )
    from agents.cadir_repair_agent import cadir_repair_node
    from agents.graph import (
        route_design_planner,
        route_complexity,
        route_incremental_step,
        route_cadir_validation,
        route_geometry_validation,
    )

    wf = StateGraph(AgentState)
    for name, fn in [
        ("input_classifier", classify_input_node),
        ("supervisor", supervisor_node),
        ("design_planner", design_planner_node),
        ("complexity_classifier", complexity_classifier_node),
        ("feature_planner", feature_planner_node),
        ("incremental_design_agent", incremental_design_agent_node),
        ("design_agent", design_agent_node),
        ("assembly_generator", assembly_generator_node),
        ("assembly_executor", assembly_executor_node),
        ("assembly_validator", assembly_validator_node),
        ("cadir_validator", cadir_validator_node),
        ("interpreter", interpreter_node),
        ("cad_executor", cad_executor_node),
        ("geometry_validator", geometry_validator_node),
        ("cadir_repair", cadir_repair_node),
    ]:
        wf.add_node(name, fn)

    wf.set_entry_point("input_classifier")
    wf.add_edge("input_classifier", "supervisor")
    wf.add_edge("supervisor", "design_planner")
    wf.add_conditional_edges(
        "design_planner",
        route_design_planner,
        {"assembly_generator": "assembly_generator", "complexity_classifier": "complexity_classifier"},
    )
    wf.add_edge("assembly_generator", "assembly_executor")
    wf.add_edge("assembly_executor", "assembly_validator")
    wf.add_edge("assembly_validator", END)
    wf.add_conditional_edges(
        "complexity_classifier",
        route_complexity,
        {"feature_planner": "feature_planner", "design_agent": "design_agent"},
    )
    wf.add_edge("design_agent", "cadir_validator")
    wf.add_edge("feature_planner", "incremental_design_agent")
    wf.add_conditional_edges(
        "incremental_design_agent",
        route_incremental_step,
        {"incremental_design_agent": "incremental_design_agent", "cadir_validator": "cadir_validator"},
    )
    wf.add_conditional_edges(
        "cadir_validator",
        route_cadir_validation,
        {"interpreter": "interpreter", "cadir_repair": "cadir_repair", "__end__": END},
    )
    wf.add_edge("interpreter", "cad_executor")
    wf.add_edge("cad_executor", "geometry_validator")
    wf.add_conditional_edges(
        "geometry_validator",
        route_geometry_validation,
        {"dfm_agent": END, "cadir_repair": "cadir_repair", "__end__": END},
    )
    wf.add_edge("cadir_repair", "cadir_validator")

    _CORE_GRAPH = wf.compile()
    return _CORE_GRAPH


def generate_core(prompt: str, design_id: str, image_path: Optional[str] = None, input_mode: str = "text-only", **_ignored):
    """Runs the workflow up to geometry validation only (fast iteration mode)."""
    started = time.time()
    try:
        final = _core_graph().invoke(_state_for(prompt, design_id, image_path, input_mode))
        return _summarise(final, started, design_id)
    except Exception as e:
        return {
            "success": False,
            "step_path": None,
            "stl_path": None,
            "error": f"core pipeline exception: {type(e).__name__}: {e}",
            "latency_sec": round(time.time() - started, 2),
            "cadir_features": [],
            "cadir_feature_count": 0,
            "design_id": design_id,
            "traceback": traceback.format_exc()[-1500:],
        }


GENERATORS = {
    "pipeline": generate_pipeline,
    "core": generate_core,
}


def get_generator(name: str):
    try:
        return GENERATORS[name]
    except KeyError:
        raise ValueError(f"Unknown generator '{name}'. Choose from {sorted(GENERATORS)}")
