"""
Tests for Upgrade 1: Symbolic Parameter Table and Pre-Execution Engineering Assertions in CADIR.
"""
import pytest
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.cadir.schema import CADIRDocument, CADIRFeature, CADIRCircle, CADIRSketchProfile
from cad.cadir.validator import validate_cadir_document, SafeMathEvaluator, resolve_symbolic_parameters


def test_safe_math_evaluator_basic():
    ctx = {"od": 100.0, "wall": 5.0, "r": 4.0}
    assert SafeMathEvaluator.eval("$od / 2.0 - $wall", ctx) == 45.0
    assert SafeMathEvaluator.eval("min($od, 80.0)", ctx) == 80.0
    assert SafeMathEvaluator.eval("sqrt(16.0)", ctx) == 4.0
    assert SafeMathEvaluator.eval("$r * 2.0 <= $wall", ctx) is False
    assert SafeMathEvaluator.eval("$r * 2.0 > $wall", ctx) is True


def test_symbolic_parameters_resolution_and_assertion_success():
    doc = CADIRDocument(
        name="Flange with Bolt Circle",
        parameters={
            "flange_od": 120.0,
            "wall_thickness": 6.0,
            "hole_diameter": 8.0,
            "hole_radius": "$hole_diameter / 2.0",
            "bolt_pcd": "$flange_od - 24.0",
            "outer_radius": "$flange_od / 2.0",
        },
        assertions=[
            "$bolt_pcd / 2.0 + $hole_radius < $outer_radius - 2.0",
            "$wall_thickness > 3.0",
        ],
        features=[
            CADIRFeature(
                id="f1_flange",
                feature_type="cylinder",
                radius="$outer_radius",
                height=15.0,
                operation="new_body",
            ),
            CADIRFeature(
                id="f2_hole",
                feature_type="hole",
                radius="$hole_radius",
                depth=15.0,
                operation="cut",
                dependencies=["f1_flange"],
            ),
        ],
    )

    res = validate_cadir_document(doc)
    assert res.is_valid, f"Expected valid doc, got errors: {res.errors}"
    assert res.resolved_parameters["hole_radius"] == 4.0
    assert res.resolved_parameters["bolt_pcd"] == 96.0
    assert doc.features[0].radius == 60.0
    assert doc.features[1].radius == 4.0
    assert doc.features[1].diameter == 8.0


def test_symbolic_parameters_assertion_failure():
    doc = CADIRDocument(
        name="Violating Part",
        parameters={
            "outer_radius": 30.0,
            "bolt_circle_radius": 28.0,
            "hole_radius": 5.0,
            "min_wall": 3.0,
        },
        assertions=[
            "$bolt_circle_radius + $hole_radius < $outer_radius - $min_wall"
        ],
        features=[
            CADIRFeature(
                id="f1",
                feature_type="cylinder",
                radius="$outer_radius",
                height=20.0,
                operation="new_body",
            ),
        ],
    )

    res = validate_cadir_document(doc)
    assert not res.is_valid
    assert any("Pre-execution engineering assertion failed" in err for err in res.errors)
