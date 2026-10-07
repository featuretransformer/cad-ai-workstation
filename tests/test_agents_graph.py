"""
Unit and Integration Tests for LangGraph CAD Multi-Agent Pipeline.
Verifies graph compilation, node execution, downstream engineering analysis,
self-healing repair loop, and Celery task compatibility.
"""
import pytest
from pathlib import Path
import sys

# Ensure backend directory is in path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.graph import cad_graph, create_cad_workflow
from agents.state import AgentState
from agents.cadir_repair_agent import cadir_repair_node
from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    CADIRSketchProfile,
    CADIRPlane,
    CADIRCircle,
)


def test_cad_graph_compilation():
    """Verify that the StateGraph compiles with all expected nodes."""
    workflow = create_cad_workflow()
    compiled = workflow.compile()
    assert compiled is not None

    expected_nodes = [
        "input_classifier",
        "supervisor",
        "design_agent",
        "cadir_validator",
        "interpreter",
        "cad_executor",
        "geometry_validator",
        "cadir_repair",
        "dfm_agent",
        "engineering_agent",
        "cost_agent",
        "safety_agent",
        "alternatives_agent",
        "cam_agent",
        "doc_agent",
    ]
    for node in expected_nodes:
        assert node in workflow.nodes, f"Missing node {node} in graph"


def test_pipeline_text_prompt_execution():
    """End-to-end execution of a parametric mechanical prompt through the graph."""
    initial_state: AgentState = {
        "design_id": "test_plate_001",
        "user_prompt": "Create a mounting plate 50x40x10 with 12mm center hole",
        "max_retries": 3,
    }

    final_state = cad_graph.invoke(initial_state)

    # CADIR and code compilation checks
    assert final_state.get("cadir_valid") is True
    assert final_state.get("cadir_document") is not None
    cad_code = final_state.get("cad_code", "")
    assert "build123d" in cad_code
    assert "result" in cad_code

    # Geometry validation & exports
    assert final_state.get("geometry_valid") is True
    assert len(final_state.get("validation_errors", [])) == 0
    exports = final_state.get("export_paths", {})
    assert "step" in exports
    assert "stl" in exports
    assert Path(exports["step"]).exists()
    assert Path(exports["stl"]).exists()

    # Downstream engineering reports
    dfm = final_state.get("dfm_report", {})
    assert dfm.get("overall_score", 0) >= 80
    assert "manufacturability" in dfm

    eng = final_state.get("engineering_report", {})
    assert eng.get("material") == "Aluminum 6061-T6"
    assert eng.get("mass_kg", 0) > 0
    assert eng.get("volume_cm3", 0) > 0

    cost = final_state.get("cost_estimate", {})
    assert cost.get("total_unit_cost_usd", 0) > 0
    assert "batch_pricing" in cost

    safety = final_state.get("safety_report", {})
    assert safety.get("safety_factor", 0) >= 1.5
    assert safety.get("status") == "PASS"

    cam = final_state.get("cam_report", {})
    assert cam.get("setup_count") >= 1
    assert len(cam.get("tool_list", [])) > 0

    doc = final_state.get("doc_report", {})
    assert "drawing_number" in doc
    assert doc.get("units") == "mm"

    alts = final_state.get("alternatives", [])
    assert len(alts) >= 2

    # Confidence scores
    conf = final_state.get("confidence_scores", {})
    assert conf.get("cadir_validator") == 1.0
    assert conf.get("geometry_validator") == 0.95
    assert conf.get("dfm_agent", 0) > 0.8


def test_pipeline_drawing_prompt_execution():
    """Verify that vector SVG drawing prompt triggers Drawing Understanding and yields 3D CAD."""
    svg_sample = """<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300">
        <rect x="20" y="20" width="80" height="60" stroke="black" fill="none" />
        <circle cx="60" cy="50" r="15" stroke="black" fill="none" />
        <text x="60" y="95">Ø30</text>
    </svg>"""

    initial_state: AgentState = {
        "design_id": "test_drawing_001",
        "user_prompt": svg_sample,
        "max_retries": 3,
    }

    final_state = cad_graph.invoke(initial_state)

    assert final_state.get("input_type") == "drawing"
    assert final_state.get("cadir_valid") is True
    assert final_state.get("geometry_valid") is True
    assert Path(final_state["export_paths"]["step"]).exists()


def test_cadir_self_healing_repair_node():
    """Verify that cadir_repair_node corrects failing parameters (e.g. oversize fillets and broken dependencies)."""
    # Create CADIR with an excessive fillet radius and broken dependency
    sk = CADIRSketchProfile(
        id="sk1",
        plane=CADIRPlane(),
        primitives=[CADIRCircle(radius=15.0)],
        is_closed=True,
    )
    doc = CADIRDocument(
        id="broken_doc",
        name="Broken Fillet Part",
        sketches=[sk],
        features=[
            CADIRFeature(
                id="f1",
                feature_type="extrude",
                sketch_id="sk1",
                distance=10.0,
                operation="new_body",
            ),
            CADIRFeature(
                id="f2",
                feature_type="fillet",
                radius=18.0,  # exceeds body height 10.0
                operation="join",
                dependencies=["non_existent_feature_id"],
            ),
        ],
    )

    state: AgentState = {
        "design_id": "test_repair_001",
        "cadir_document": doc,
        "cadir_errors": ["Dependency non_existent_feature_id not found"],
        "last_error": "Fillet operation failed: radius exceeds geometry boundaries",
        "repair_attempts": 0,
        "error_count": 0,
    }

    repair_result = cadir_repair_node(state)
    assert repair_result.get("repair_attempts") == 1
    assert repair_result.get("error_count") == 1

    repaired_doc = repair_result["cadir_document"]
    # Check that fillet radius was reduced
    fillet_f = next(f for f in repaired_doc.features if f.feature_type == "fillet")
    assert fillet_f.radius < 18.0


def test_celery_task_streaming_compatibility():
    """Verify that streaming updates through cad_graph matches Celery task expectations."""
    initial_state: AgentState = {
        "design_id": "test_stream_001",
        "session_id": "sess_123",
        "user_prompt": "hex nut 25mm diameter",
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
        "max_retries": 3,
        "last_error": "",
        "messages": [],
    }

    nodes_visited = []
    for event in cad_graph.stream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            nodes_visited.append(node_name)
            assert isinstance(node_output, dict)

    assert "input_classifier" in nodes_visited
    assert "supervisor" in nodes_visited
    assert "design_agent" in nodes_visited
    assert "cadir_validator" in nodes_visited
    assert "interpreter" in nodes_visited
    assert "cad_executor" in nodes_visited
    assert "geometry_validator" in nodes_visited
    assert "dfm_agent" in nodes_visited
    assert "engineering_agent" in nodes_visited
    assert "cost_agent" in nodes_visited
    assert "doc_agent" in nodes_visited
