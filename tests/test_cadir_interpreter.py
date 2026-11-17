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


def test_interpreter_topological_selectors():
    """Verify code generation with semantic face and edge selectors (Upgrade 2)."""
    doc = CADIRDocument(
        id="topological_doc",
        name="Topological Test",
        features=[
            CADIRFeature(
                id="f1_base",
                feature_type="box",
                length=60.0,
                width=40.0,
                height=20.0,
                operation="new_body",
            ),
            CADIRFeature(
                id="f2_top_hole",
                feature_type="hole",
                target_face_selector="top",
                diameter=10.0,
                depth=15.0,
                dependencies=["f1_base"],
            ),
            CADIRFeature(
                id="f3_fillet",
                feature_type="fillet",
                target_edge_selector="all_vertical",
                radius=2.0,
                dependencies=["f1_base"],
            ),
        ],
    )
    code = generate_build123d_code(doc)
    assert "p.faces().sort_by(Axis.Z)[-1]" in code
    assert "_edges = p.edges().filter_by(Axis.Z)" in code
    assert "step_volumes.append" in code


def test_interpreter_sketch_constraint_solver():
    """Verify 2D sketch constraint solver convergence (Upgrade 4)."""
    from cad.cadir.schema import CADIRLine, CADIRConstraint
    from cad.cadir.interpreter import solve_sketch_constraints

    l1 = CADIRLine(
        id="l1",
        start=Point3D(x=0.0, y=0.0, z=0.0),
        end=Point3D(x=10.0, y=0.5, z=0.0),
    )
    l2 = CADIRLine(
        id="l2",
        start=Point3D(x=10.2, y=0.5, z=0.0),
        end=Point3D(x=10.2, y=20.0, z=0.0),
    )
    sketch = CADIRSketchProfile(
        id="sk_constrained",
        primitives=[l1, l2],
        constraints=[
            CADIRConstraint(
                constraint_type="fixed",
                entities=["l1_start"],
            ),
            CADIRConstraint(
                constraint_type="horizontal",
                entities=["l1_start", "l1_end"],
            ),
            CADIRConstraint(
                constraint_type="coincident",
                entities=["l1_end", "l2_start"],
            ),
            CADIRConstraint(
                constraint_type="distance",
                entities=["l1_start", "l1_end"],
                value=25.0,
            ),
        ],
    )
    solved = solve_sketch_constraints(sketch)
    # l1 should now be horizontal with length 25 and l2_start coincident with l1_end
    p1_end = solved.primitives[0].end
    p2_start = solved.primitives[1].start
    assert abs(p1_end.x - 25.0) < 1e-4
    assert abs(p1_end.y - 0.0) < 1e-4
    assert abs(p2_start.x - p1_end.x) < 1e-4
    assert abs(p2_start.y - p1_end.y) < 1e-4


def test_interpreter_hardware_macros():
    """Verify standard hardware and gear macro code generation (Upgrade 6)."""
    doc = CADIRDocument(
        id="macro_doc",
        name="Macro Hardware Component",
        features=[
            CADIRFeature(
                id="f1_bolt",
                feature_type="iso_bolt",
                diameter=10.0,
                length=50.0,
                operation="new_body",
            ),
            CADIRFeature(
                id="f2_gear",
                feature_type="spur_gear_macro",
                module=2.5,
                teeth=28,
                face_width=16.0,
                bore_diameter=12.0,
                operation="join",
                dependencies=["f1_bolt"],
            ),
        ],
    )
    code = generate_build123d_code(doc)
    assert "ISO 4014 Standard Bolt" in code
    assert "_rp = _m * _N / 2.0" in code
    assert "Hole(radius=6.0, depth=None)" in code


