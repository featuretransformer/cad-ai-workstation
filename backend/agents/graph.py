"""
LangGraph Multi-Agent CAD Generation Workflow.
Connects input classification, intent parsing, few-shot dataset retrieval,
parametric CADIR synthesis, deterministic build123d code interpretation,
sandboxed CAD execution, physical geometry validation, self-healing repair,
and downstream engineering analysis reports.
"""
from typing import Literal
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.input_classifier import classify_input_node
from agents.supervisor import supervisor_node
from agents.design_agent import design_agent_node
from agents.validator_nodes import (
    cadir_validator_node,
    interpreter_node,
    cad_executor_node,
    geometry_validator_node,
)
from agents.cadir_repair_agent import cadir_repair_node
from agents.downstream_nodes import (
    dfm_agent_node,
    engineering_agent_node,
    cost_agent_node,
    safety_agent_node,
    alternatives_agent_node,
    cam_agent_node,
    doc_agent_node,
)


def route_cadir_validation(state: AgentState) -> Literal["interpreter", "cadir_repair", "__end__"]:
    """
    Routes from CADIR validation: proceed to interpreter if valid,
    or route to self-healing repair loop if retries remain.
    """
    if state.get("cadir_valid", False):
        return "interpreter"

    max_retries = state.get("max_retries", 3)
    attempts = state.get("repair_attempts", 0)
    if attempts < max_retries:
        return "cadir_repair"

    return "__end__"


def route_geometry_validation(state: AgentState) -> Literal["dfm_agent", "cadir_repair", "__end__"]:
    """
    Routes from physical geometry validation: proceed to downstream DFM analysis if valid,
    or route to CADIR repair agent if retries remain.
    """
    if state.get("geometry_valid", False):
        return "dfm_agent"

    max_retries = state.get("max_retries", 3)
    attempts = state.get("repair_attempts", 0)
    if attempts < max_retries:
        return "cadir_repair"

    return "__end__"


def create_cad_workflow() -> StateGraph:
    """Builds and compiles the full LangGraph CAD generation pipeline."""
    workflow = StateGraph(AgentState)

    # 1. Register All Agent Nodes
    workflow.add_node("input_classifier", classify_input_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("design_agent", design_agent_node)
    workflow.add_node("cadir_validator", cadir_validator_node)
    workflow.add_node("interpreter", interpreter_node)
    workflow.add_node("cad_executor", cad_executor_node)
    workflow.add_node("geometry_validator", geometry_validator_node)
    workflow.add_node("cadir_repair", cadir_repair_node)

    # Downstream Analysis Nodes
    workflow.add_node("dfm_agent", dfm_agent_node)
    workflow.add_node("engineering_agent", engineering_agent_node)
    workflow.add_node("cost_agent", cost_agent_node)
    workflow.add_node("safety_agent", safety_agent_node)
    workflow.add_node("alternatives_agent", alternatives_agent_node)
    workflow.add_node("cam_agent", cam_agent_node)
    workflow.add_node("doc_agent", doc_agent_node)

    # 2. Define Workflow Edges & Routing
    workflow.set_entry_point("input_classifier")
    workflow.add_edge("input_classifier", "supervisor")
    workflow.add_edge("supervisor", "design_agent")
    workflow.add_edge("design_agent", "cadir_validator")

    # Conditional Branch 1: CADIR Validation Check
    workflow.add_conditional_edges(
        "cadir_validator",
        route_cadir_validation,
        {
            "interpreter": "interpreter",
            "cadir_repair": "cadir_repair",
            "__end__": END,
        },
    )

    workflow.add_edge("interpreter", "cad_executor")
    workflow.add_edge("cad_executor", "geometry_validator")

    # Conditional Branch 2: Physical Geometry Validation Check
    workflow.add_conditional_edges(
        "geometry_validator",
        route_geometry_validation,
        {
            "dfm_agent": "dfm_agent",
            "cadir_repair": "cadir_repair",
            "__end__": END,
        },
    )

    # Self-Healing Retry Loop: return to CADIR validator
    workflow.add_edge("cadir_repair", "cadir_validator")

    # Downstream Engineering Sequence
    workflow.add_edge("dfm_agent", "engineering_agent")
    workflow.add_edge("engineering_agent", "cost_agent")
    workflow.add_edge("cost_agent", "safety_agent")
    workflow.add_edge("safety_agent", "alternatives_agent")
    workflow.add_edge("alternatives_agent", "cam_agent")
    workflow.add_edge("cam_agent", "doc_agent")
    workflow.add_edge("doc_agent", END)

    return workflow


# Compile the production pipeline
cad_graph = create_cad_workflow().compile()
