"""
Assembly Pipeline & Complex CAD Roadmap Test Suite.
Validates:
1. Assembly Schema & Data Structures (AssemblySpec, ComponentSpec, MatingInterface, Placement3D)
2. Design Planner Agent & Mechanical Decomposition (Three-Finger Gripper benchmark, Gearbox, Caster)
3. Per-Component Parametric CADIR Generation
4. Assembly Execution & Multi-Body Compound Construction via build123d
5. Assembly Validation (OpenCASCADE boolean interference & clearance verification)
6. Enhanced CADIR Features (sweep, loft, shell, rib, thread)
7. Parameter Propagation Engine
8. Full LangGraph Assembly Workflow Integration & Single-Part Regression
"""
import pytest
import os
from pathlib import Path

from cad.assembly.schema import (
    AssemblySpec,
    ComponentSpec,
    MatingInterface,
    Placement3D,
)
from cad.assembly.component_generator import generate_component_cadir
from cad.assembly.executor import execute_assembly
from cad.assembly.validator import validate_assembly
from cad.assembly.parameter_engine import propagate_assembly_parameters
from agents.design_planner import plan_assembly, is_assembly_prompt
from agents.graph import cad_graph
from agents.state import AgentState
from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    CADIRSketchProfile,
    CADIRPlane,
    CADIRCircle,
    CADIRRectangle,
    Point3D,
)
from cad.cadir.validator import validate_cadir_document
from cad.cadir.interpreter import generate_build123d_code


def test_assembly_schema_validation():
    """Verify AssemblySpec, ComponentSpec, and MatingInterface schema integrity."""
    spec = AssemblySpec(
        id="asm_test_01",
        name="Test Flange Assembly",
        components=[
            ComponentSpec(
                component_id="comp_1",
                name="Base Flange",
                role="mounting_plate",
                quantity=1,
                parameters={"diameter": 100.0, "thickness": 10.0},
            ),
            ComponentSpec(
                component_id="comp_2",
                name="Coupling Pin",
                role="pivot_pin",
                quantity=2,
                parameters={"diameter": 8.0, "length": 20.0},
            ),
        ],
        mating_interfaces=[
            MatingInterface(
                parent_component_id="comp_1",
                child_component_id="comp_2",
                mate_type="cylindrical",
                clearance=0.1,
            )
        ],
        assumptions=["Standard ISO tolerances"],
        unresolved_parameters=["Fastener grade"],
    )

    assert spec.id == "asm_test_01"
    assert len(spec.components) == 2
    bom = spec.get_bom()
    assert len(bom) == 2
    assert bom[0]["name"] == "Base Flange"
    assert bom[1]["quantity"] == 2

    # Verify JSON roundtrip
    json_str = spec.to_json()
    loaded = AssemblySpec.from_json(json_str)
    assert loaded.name == spec.name
    assert len(loaded.components) == 2


def test_three_finger_gripper_benchmark_decomposition():
    """
    Acceptance Criteria Test:
    Verify Three-Finger Gripper Benchmark decomposition into:
    mounting plate, 3 fingers, pivots, links, actuator.
    """
    prompt = "Design a three-finger robotic gripper assembly with mounting plate, fingers, pins, links and actuator"
    assert is_assembly_prompt(prompt)

    spec = plan_assembly("gripper_bench_01", prompt)
    assert spec.assembly_family == "gripper"
    assert len(spec.components) == 5

    roles = [c.role for c in spec.components]
    assert "mounting_plate" in roles
    assert "finger" in roles
    assert "pivot_pin" in roles
    assert "linkage" in roles
    assert "actuator" in roles

    # Quantities: 1 plate, 3 fingers, 3 pins, 3 links, 1 actuator = 11 parts
    total_instances = sum(c.quantity for c in spec.components)
    assert total_instances == 11

    # Verify assumptions & unresolved parameters are reported
    assert len(spec.assumptions) >= 2
    assert len(spec.unresolved_parameters) >= 1


def test_three_finger_gripper_execution_and_exports(tmp_path):
    """
    Acceptance Criteria Test:
    Execute Three-Finger Gripper Assembly in build123d.
    Verify multi-body STEP, STL, and GLB exports with separate solids.
    """
    spec = plan_assembly("bench_exec_01", "three-finger gripper assembly")
    out_dir = str(tmp_path / "gripper_exports")

    res = execute_assembly(spec, "bench_exec_01", output_dir=out_dir)
    assert res.get("success") is True
    assert res.get("solids_count") >= 11  # Multi-body solids count
    assert res.get("volume") > 10000.0

    # Verify export file paths exist
    step_path = res.get("step_path")
    stl_path = res.get("stl_path")
    assert step_path and os.path.exists(step_path)
    assert stl_path and os.path.exists(stl_path)
    assert os.path.getsize(step_path) > 1000
    assert os.path.getsize(stl_path) > 1000

    # Verify per-component STLs generated
    comp_exports = res.get("component_exports", {})
    assert len(comp_exports) >= 4


def test_three_finger_gripper_validation():
    """
    Acceptance Criteria Test:
    Verify interference, clearance, and envelope validation on assembled gripper.
    """
    spec = plan_assembly("bench_val_01", "three-finger gripper assembly")
    res = execute_assembly(spec, "bench_val_01")
    val_report = validate_assembly(spec, res)

    assert val_report["is_valid"] is True
    assert "envelope_metrics" in val_report
    env = val_report["envelope_metrics"]
    assert env["span_x"] > 50.0
    assert env["span_y"] > 50.0
    assert env["span_z"] > 50.0
    assert len(val_report.get("clearances", [])) >= 3


def test_enhanced_cadir_features():
    """
    Roadmap Phase 6 Test:
    Verify sweep, loft, shell, rib, and thread features in schema and interpreter.
    """
    # 1. Shell Feature
    doc_shell = CADIRDocument(
        id="doc_shell_test",
        name="Thin Wall Enclosure",
        features=[
            CADIRFeature(
                id="f1_box",
                feature_type="box",
                length=40.0,
                width=40.0,
                height=30.0,
                dependencies=[],
            ),
            CADIRFeature(
                id="f2_shell",
                feature_type="shell",
                thickness=2.5,
                opening_faces=["top"],
                dependencies=["f1_box"],
            ),
        ],
    )
    val = validate_cadir_document(doc_shell)
    assert val.is_valid
    code = generate_build123d_code(doc_shell)
    assert "offset" in code

    # 2. Thread Feature
    doc_thread = CADIRDocument(
        id="doc_thread_test",
        name="M12 Stud",
        features=[
            CADIRFeature(
                id="f1_thread",
                feature_type="thread",
                thread_diameter=12.0,
                thread_length=40.0,
                pitch=1.75,
                dependencies=[],
            )
        ],
    )
    val2 = validate_cadir_document(doc_thread)
    assert val2.is_valid
    code2 = generate_build123d_code(doc_thread)
    assert "Cylinder" in code2
    assert "chamfer" in code2

    # 3. Loft Feature
    doc_loft = CADIRDocument(
        id="doc_loft_test",
        name="Square to Round Adapter",
        sketches=[
            CADIRSketchProfile(
                id="sk1",
                plane=CADIRPlane(origin=Point3D(x=0, y=0, z=0)),
                primitives=[CADIRRectangle(width=30.0, height=30.0)],
            ),
            CADIRSketchProfile(
                id="sk2",
                plane=CADIRPlane(origin=Point3D(x=0, y=0, z=40.0)),
                primitives=[CADIRCircle(radius=10.0)],
            ),
        ],
        features=[
            CADIRFeature(
                id="f1_loft",
                feature_type="loft",
                section_sketch_ids=["sk1", "sk2"],
                dependencies=[],
            )
        ],
    )
    val3 = validate_cadir_document(doc_loft)
    assert val3.is_valid
    code3 = generate_build123d_code(doc_loft)
    assert "loft" in code3


def test_parameter_propagation_engine():
    """
    Roadmap Phase 7 Test:
    Verify parameter change propagation updates dependent components and placements.
    """
    spec = plan_assembly("param_test_01", "three-finger gripper")
    orig_dia = spec.components[0].parameters["diameter"]

    # Propagate larger mounting diameter
    updated = propagate_assembly_parameters(
        spec,
        {"mounting_diameter": 160.0, "finger_length": 95.0, "stroke": 35.0},
    )

    assert updated.global_parameters["mounting_diameter"] == 160.0
    plate = updated.components[0]
    assert plate.parameters["diameter"] == 160.0
    assert plate.parameters["mount_radius"] == 60.0  # 160 * 0.375

    finger = updated.components[1]
    assert finger.parameters["length"] == 95.0
    # Placements must reflect new 60mm mount radius
    assert finger.instance_placements[0].translation.x == 60.0


def test_langgraph_assembly_pipeline_execution():
    """
    Full LangGraph Integration Test:
    Execute assembly prompt through the compiled LangGraph workflow.
    Verify execution flows through design_planner -> assembly_generator -> assembly_executor -> assembly_validator -> downstream!
    """
    initial_state: AgentState = {
        "design_id": "lg_asm_test_01",
        "user_prompt": "Build a three-finger robotic gripper assembly",
        "parsed_intent": {},
        "error_count": 0,
        "max_retries": 1,
    }

    final_state = cad_graph.invoke(initial_state)

    assert final_state.get("is_assembly") is True
    assert final_state.get("assembly_spec") is not None
    assert final_state.get("geometry_valid") is True
    assert final_state.get("execution_result", {}).get("success") is True
    assert final_state.get("export_paths", {}).get("step") is not None

    # Downstream analysis reports must be generated
    assert final_state.get("dfm_report")
    assert final_state.get("engineering_report", {}).get("is_assembly") is True
    assert final_state.get("engineering_report", {}).get("bill_of_materials")
    assert final_state.get("doc_report")


def test_single_part_regression_compatibility():
    """
    Regression Test:
    Verify existing single-part prompt routes through single-part pathway without regression.
    """
    initial_state: AgentState = {
        "design_id": "lg_single_part_01",
        "user_prompt": "Machined mounting bracket 50x40x5mm with two M8 holes",
        "parsed_intent": {},
        "error_count": 0,
        "max_retries": 1,
    }

    final_state = cad_graph.invoke(initial_state)

    assert final_state.get("is_assembly") is False
    assert final_state.get("cadir_valid") is True
    assert final_state.get("geometry_valid") is True
    assert final_state.get("execution_result", {}).get("success") is True
    assert final_state.get("export_paths", {}).get("step") is not None
