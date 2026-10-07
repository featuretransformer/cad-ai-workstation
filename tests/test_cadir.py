"""
Unit tests for CAD Intermediate Representation (CADIR) schema and validator.
Phase 1 Foundation Verification.
"""
import pytest
import sys
from pathlib import Path

# Ensure backend is in sys.path
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
from cad.cadir.validator import validate_cadir_document
from agents.state import AgentState


def test_valid_primitive_box():
    """Verify that a simple 3D primitive box passes CADIR validation."""
    doc = CADIRDocument(
        id="doc_box_01",
        name="Simple Cube",
        component_family="primitive",
        difficulty="L1",
        units="mm",
        material="Aluminum 6061",
        features=[
            CADIRFeature(
                id="f1_box",
                name="Base Box",
                feature_type="box",
                length=50.0,
                width=50.0,
                height=50.0,
                dependencies=[],
            )
        ],
    )

    result = validate_cadir_document(doc)
    assert result.is_valid, f"Validation failed: {result.errors}"
    assert result.topological_order == ["f1_box"]
    assert result.feature_depths["f1_box"] == 0


def test_complex_mechanical_component():
    """
    Verify a multi-feature mechanical part:
    Base Sketch -> Extrude Plate -> Hole -> Fillet.
    Ensures dependency DAG resolution and depth calculation.
    """
    doc = CADIRDocument(
        id="doc_flange_02",
        name="Mounting Flange",
        component_family="flange",
        difficulty="L3",
        units="mm",
        parameters={"plate_w": 100.0, "plate_h": 60.0, "thickness": 12.0, "bore_dia": 25.0},
        sketches=[
            CADIRSketchProfile(
                id="sk1_base",
                name="Base Rectangle",
                plane=CADIRPlane(),
                primitives=[
                    CADIRRectangle(width=100.0, height=60.0, center=Point3D(x=0, y=0, z=0))
                ],
            )
        ],
        features=[
            CADIRFeature(
                id="f1_base_extrude",
                name="Extrude Base Plate",
                feature_type="extrude",
                sketch_id="sk1_base",
                distance=12.0,
                dependencies=[],
            ),
            CADIRFeature(
                id="f2_center_hole",
                name="Center Bore",
                feature_type="hole",
                diameter=25.0,
                depth=12.0,
                position=Point3D(x=0, y=0, z=0),
                dependencies=["f1_base_extrude"],
            ),
            CADIRFeature(
                id="f3_edge_fillet",
                name="Top Outer Edge Fillet",
                feature_type="fillet",
                radius=2.0,
                edge_selector="top",
                dependencies=["f2_center_hole"],
            ),
        ],
    )

    result = validate_cadir_document(doc)
    assert result.is_valid, f"Validation failed: {result.errors}"
    assert result.topological_order == ["f1_base_extrude", "f2_center_hole", "f3_edge_fillet"]
    assert result.feature_depths["f1_base_extrude"] == 0
    assert result.feature_depths["f2_center_hole"] == 1
    assert result.feature_depths["f3_edge_fillet"] == 2


def test_json_roundtrip_fidelity():
    """Verify lossless serialization and deserialization via JSON."""
    doc = CADIRDocument(
        id="doc_json_test",
        name="Shaft Collar",
        component_family="collar",
        features=[
            CADIRFeature(
                id="f1_cyl",
                feature_type="cylinder",
                radius=20.0,
                height=15.0,
                dependencies=[],
            )
        ],
    )

    json_str = doc.to_json()
    loaded_doc = CADIRDocument.from_json(json_str)
    assert loaded_doc.id == doc.id
    assert loaded_doc.name == doc.name
    assert loaded_doc.features[0].radius == 20.0

    result = validate_cadir_document(loaded_doc)
    assert result.is_valid


def test_rejection_of_missing_dependency():
    """Detect and reject references to non-existent dependencies."""
    doc = CADIRDocument(
        id="doc_bad_dep",
        name="Broken Part",
        features=[
            CADIRFeature(
                id="f1_hole",
                feature_type="hole",
                diameter=10.0,
                depth=10.0,
                dependencies=["non_existent_feature_id"],
            )
        ],
    )

    result = validate_cadir_document(doc)
    assert not result.is_valid
    assert any("non-existent feature" in err for err in result.errors)


def test_rejection_of_forward_reference():
    """Detect and reject dependencies that reference features later in the sequence."""
    doc = CADIRDocument(
        id="doc_forward_ref",
        name="Invalid Order Part",
        features=[
            CADIRFeature(
                id="f1_fillet",
                feature_type="fillet",
                radius=2.0,
                dependencies=["f2_box"],  # Forward reference
            ),
            CADIRFeature(
                id="f2_box",
                feature_type="box",
                length=30.0,
                width=30.0,
                height=30.0,
                dependencies=[],
            ),
        ],
    )

    result = validate_cadir_document(doc)
    assert not result.is_valid
    assert any("forward-references" in err for err in result.errors)


def test_rejection_of_nonexistent_sketch():
    """Detect and reject features referencing non-existent sketch IDs."""
    doc = CADIRDocument(
        id="doc_bad_sketch",
        name="Missing Sketch",
        features=[
            CADIRFeature(
                id="f1_extrude",
                feature_type="extrude",
                sketch_id="missing_sketch_99",
                distance=10.0,
                dependencies=[],
            )
        ],
    )

    result = validate_cadir_document(doc)
    assert not result.is_valid
    assert any("references non-existent sketch" in err for err in result.errors)


def test_rejection_of_negative_dimensions():
    """Verify that negative/zero dimensions are blocked by Pydantic and validator."""
    with pytest.raises(Exception):
        CADIRFeature(
            id="f_invalid",
            feature_type="box",
            length=-10.0,  # Must be gt=0.0
            width=20.0,
            height=20.0,
        )


def test_agent_state_cadir_integration():
    """Verify that AgentState accommodates CADIR fields alongside legacy keys."""
    state: AgentState = {
        "design_id": "des-1234",
        "user_prompt": "Create a mounting flange",
        "cad_code": "Box(10, 10, 10)",
        "geometry_valid": True,
        # CADIR extensions:
        "cadir_document": {"id": "doc-01", "name": "Flange"},
        "cadir_valid": True,
        "cadir_errors": [],
        "retrieved_examples": [],
        "repair_attempts": 0,
    }

    assert state["design_id"] == "des-1234"
    assert state["cadir_valid"] is True
    assert state["cadir_document"]["name"] == "Flange"


def test_rejection_of_self_dependency():
    """Detect and reject a feature depending on itself."""
    doc = CADIRDocument(
        id="doc_self_dep",
        name="Self Ref",
        features=[
            CADIRFeature(
                id="f1_box",
                feature_type="box",
                length=10.0,
                width=10.0,
                height=10.0,
                dependencies=["f1_box"],
            )
        ],
    )
    result = validate_cadir_document(doc)
    assert not result.is_valid
    assert any("Dependencies must strictly precede" in err for err in result.errors)

