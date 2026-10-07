"""
Unit tests for deterministic CADIR -> build123d interpreter.
Phase 3 Verification: Code Generation, Execution, and Geometry Validation.
"""
import pytest
import sys
import os
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    CADIRSketchProfile,
    CADIRPlane,
    CADIRRectangle,
    CADIRCircle,
    Point3D,
    Vector3D,
)
from cad.cadir.interpreter import generate_build123d_code, interpret_and_execute
from cad.validator import validate_step, validate_mesh


def test_interpreter_box_code_generation():
    """Verify code generation for a 3D box primitive."""
    doc = CADIRDocument(
        id="interp_box_doc",
        name="Parametric Block",
        parameters={"block_len": 50.0},
        features=[
            CADIRFeature(
                id="f1_box",
                feature_type="box",
                length=50.0,
                width=30.0,
                height=15.0,
            )
        ],
    )

    code = generate_build123d_code(doc)
    assert "from build123d import *" in code
    assert "with BuildPart() as p:" in code
    assert "Box(length=50.0, width=30.0, height=15.0, mode=Mode.ADD)" in code
    assert "result = p.part" in code


def test_interpreter_sketch_extrude_hole_fillet_generation():
    """Verify code generation for multi-feature: Extrude Plate + Hole + Fillet."""
    doc = CADIRDocument(
        id="interp_flange_doc",
        name="Mounting Plate",
        sketches=[
            CADIRSketchProfile(
                id="sk1",
                plane=CADIRPlane(),
                primitives=[CADIRRectangle(width=80.0, height=50.0)],
            )
        ],
        features=[
            CADIRFeature(
                id="f1_extrude",
                feature_type="extrude",
                sketch_id="sk1",
                distance=10.0,
            ),
            CADIRFeature(
                id="f2_hole",
                feature_type="hole",
                diameter=12.0,
                depth=10.0,
                position=Point3D(x=0, y=0, z=0),
                dependencies=["f1_extrude"],
            ),
            CADIRFeature(
                id="f3_fillet",
                feature_type="fillet",
                radius=1.5,
                edge_selector="top",
                dependencies=["f2_hole"],
            ),
        ],
    )

    code = generate_build123d_code(doc)
    assert "with BuildSketch" in code
    assert "Rectangle(width=80.0, height=50.0)" in code
    assert "extrude(amount=10.0, mode=Mode.ADD)" in code
    assert "Hole(radius=6.0, depth=10.0)" in code
    assert "fillet(_edges, radius=1.5)" in code


def test_interpreter_rejection_of_invalid_doc():
    """Verify interpreter refuses to generate code for broken/invalid CADIR."""
    doc = CADIRDocument(
        id="broken_doc",
        name="Broken",
        features=[
            CADIRFeature(
                id="f1_extrude",
                feature_type="extrude",
                sketch_id="non_existent_sketch",
                distance=10.0,
            )
        ],
    )
    with pytest.raises(ValueError) as excinfo:
        generate_build123d_code(doc)
    assert "Cannot interpret invalid CADIR document" in str(excinfo.value)


def test_interpret_and_execute_box():
    """
    Full end-to-end test:
    CADIR Document -> build123d code -> subprocess executor -> STEP export -> validation.
    """
    # Check if build123d is available in environment
    try:
        import build123d
    except ImportError:
        pytest.skip("build123d not yet installed in active test runner")

    doc = CADIRDocument(
        id="e2e_box_doc",
        name="E2E Box",
        features=[
            CADIRFeature(
                id="f1_box",
                feature_type="box",
                length=40.0,
                width=20.0,
                height=10.0,
            )
        ],
    )

    exec_result = interpret_and_execute(doc, design_id="test_e2e_box")
    assert exec_result["success"] is True, f"CAD execution failed: {exec_result.get('error')}"

    # Verify geometry properties
    step_path = exec_result.get("step_path")
    stl_path = exec_result.get("stl_path")
    assert step_path and os.path.exists(step_path)
    assert stl_path and os.path.exists(stl_path)

    # Validate STEP
    step_val = validate_step(step_path)
    assert step_val["valid"] is True, f"STEP validation failed: {step_val['errors']}"

    # Validate Mesh
    mesh_val = validate_mesh(stl_path)
    assert mesh_val["valid"] is True, f"Mesh validation failed: {mesh_val['errors']}"
    assert mesh_val["stats"]["is_watertight"] is True
    assert mesh_val["stats"]["volume"] > 0


def test_interpret_and_execute_plate_with_hole():
    """
    End-to-end test of Sketch + Extrude + Hole:
    CADIR Document -> build123d code -> executor -> STEP/STL export -> validation.
    """
    try:
        import build123d
    except ImportError:
        pytest.skip("build123d not yet installed")

    doc = CADIRDocument(
        id="e2e_plate_hole_doc",
        name="Mounting Plate With Hole",
        sketches=[
            CADIRSketchProfile(
                id="sk_base",
                plane=CADIRPlane(),
                primitives=[CADIRRectangle(width=60.0, height=40.0)],
            )
        ],
        features=[
            CADIRFeature(
                id="f1_plate",
                feature_type="extrude",
                sketch_id="sk_base",
                distance=8.0,
            ),
            CADIRFeature(
                id="f2_hole",
                feature_type="hole",
                diameter=10.0,
                depth=8.0,
                position=Point3D(x=0, y=0, z=0),
                dependencies=["f1_plate"],
            ),
        ],
    )

    exec_result = interpret_and_execute(doc, design_id="test_e2e_plate_hole")
    assert exec_result["success"] is True, f"CAD execution failed: {exec_result.get('error')}"

    step_path = exec_result.get("step_path")
    stl_path = exec_result.get("stl_path")
    assert step_path and os.path.exists(step_path)
    assert stl_path and os.path.exists(stl_path)

    # Validate STEP and Mesh
    step_val = validate_step(step_path)
    assert step_val["valid"] is True, f"STEP validation failed: {step_val['errors']}"
    mesh_val = validate_mesh(stl_path)
    assert mesh_val["valid"] is True, f"Mesh validation failed: {mesh_val['errors']}"
    assert mesh_val["stats"]["is_watertight"] is True
    assert 18000 < mesh_val["stats"]["volume"] < 19000

