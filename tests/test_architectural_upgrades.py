"""
Comprehensive Verification Suite for the 7 Deterministic Architectural Upgrades:
1. Symbolic Parameter Table ("Plan-Then-Point" in CADIR)
2. Semantic Topological Face Tagging (Banning Raw 3D Plane Coordinates)
3. Step-by-Step Incremental Execution & Non-Zero Volume-Delta (ΔV) Verification
4. 2D Geometric Constraint Solver for Sketch-to-CAD
5. Multi-View Set-of-Mark (SoM) Visual Critic Node
6. Lightweight Macro RAG Index (Zero-To-CAD-1m + bd_warehouse + gggears)
7. Execution-Guided Best-of-N Candidate Sampling & Parameter Snapping
"""
from pathlib import Path
import pytest
import sys
import json

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    CADIRSketchProfile,
    CADIRRectangle,
    CADIRCircle,
    CADIRConstraint,
    Point3D,
)
from cad.cadir.validator import (
    resolve_symbolic_parameters,
    validate_cadir_document,
)
from cad.cadir.interpreter import (
    cadir_to_build123d,
    solve_sketch_constraints,
)
from cad.validator import (
    verify_volume_deltas,
    SilentMergeError,
    NullBooleanCutError,
    score_cadir_candidate,
)
from utils.macro_rag import query_macro_rag
from agents.design_agent import snap_cadir_parameters
from agents.validator_nodes import visual_verifier_node


# ─────────────────────────────────────────────────────────────────────────────
# 1. Symbolic Parameter Table ("Plan-Then-Point" in CADIR)
# ─────────────────────────────────────────────────────────────────────────────
def test_symbolic_parameter_table_and_assertions():
    doc = CADIRDocument(
        id="test_flange_symbolic",
        name="Parametric Pipe Flange",
        parameters={
            "flange_od": 150.0,
            "wall_thickness": 12.0,
            "bolt_circle_r": "$flange_od / 2 - 20",
            "hole_dia": 10.0,
            "hole_r": "$hole_dia / 2",
        },
        assertions=[
            "$bolt_circle_r + $hole_r < $flange_od / 2",
            "$wall_thickness >= 5.0",
        ],
        features=[
            CADIRFeature(
                id="f1_base",
                name="Flange Base",
                feature_type="cylinder",
                radius="$flange_od / 2",
                height="$wall_thickness",
                operation="new_body",
            ),
            CADIRFeature(
                id="f2_hole",
                name="Bolt Hole",
                feature_type="hole",
                diameter="$hole_dia",
                depth="$wall_thickness + 5",
                target_face_selector="top",
                pattern_radius="$bolt_circle_r",
                operation="cut",
            ),
        ]
    )

    resolved, errs = resolve_symbolic_parameters(doc)
    assert len(errs) == 0
    assert resolved.parameters["bolt_circle_r"] == 55.0
    assert resolved.parameters["hole_r"] == 5.0
    assert resolved.features[0].radius == 75.0
    assert resolved.features[0].height == 12.0
    assert resolved.features[1].diameter == 10.0
    assert resolved.features[1].depth == 17.0
    assert resolved.features[1].pattern_radius == 55.0

    # Test assertion violation returns validation error
    doc.assertions.append("$flange_od < 100")
    _, fail_errs = resolve_symbolic_parameters(doc)
    assert any("assertion failed" in e.lower() for e in fail_errs)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Semantic Topological Face Tagging
# ─────────────────────────────────────────────────────────────────────────────
def test_semantic_topological_selectors_compilation():
    doc = CADIRDocument(
        id="test_topological_dsl",
        name="Block with Selectors",
        features=[
            CADIRFeature(
                id="f_block",
                name="Base Block",
                feature_type="box",
                length=100.0,
                width=80.0,
                height=40.0,
                operation="new_body",
            ),
            CADIRFeature(
                id="f_top_hole",
                name="Top Mounted Hole",
                feature_type="hole",
                diameter=12.0,
                depth=20.0,
                target_face_selector="top",
                operation="cut",
            ),
            CADIRFeature(
                id="f_front_pocket",
                name="Front Cavity",
                feature_type="pocket",
                length=30.0,
                width=20.0,
                depth=15.0,
                target_face_selector="front",
                operation="cut",
            ),
            CADIRFeature(
                id="f_fillet",
                name="Vertical Edges Fillet",
                feature_type="fillet",
                radius=3.0,
                target_edge_selector="all_vertical",
                operation="join",
            ),
            CADIRFeature(
                id="f_chamfer",
                name="Top Perimeter Chamfer",
                feature_type="chamfer",
                distance=1.5,
                target_edge_selector="top_perimeter",
                operation="join",
            ),
        ]
    )

    code = cadir_to_build123d(doc)
    assert "faces().sort_by(Axis.Z)[-1]" in code
    assert "faces().sort_by(Axis.Y)[0]" in code
    assert "edges().filter_by(Axis.Z)" in code
    assert "_top_face = p.faces().sort_by(Axis.Z)[-1:]" in code
    assert "_edges = _top_face.edges()" in code


# ─────────────────────────────────────────────────────────────────────────────
# 3. Step-by-Step Volume-Delta (ΔV) Invariants
# ─────────────────────────────────────────────────────────────────────────────
def test_volume_delta_invariants():
    # A valid progression (initial step + 2 subsequent operations)
    valid_step_vols = [
        {"feature_id": "f1_base", "feature_type": "box", "operation": "new_body", "volume": 10000.0},
        {"feature_id": "f2_boss", "feature_type": "cylinder", "operation": "join", "volume": 12500.0},
        {"feature_id": "f3_hole", "feature_type": "hole", "operation": "cut", "volume": 11800.0},
    ]
    res = verify_volume_deltas(valid_step_vols)
    assert res["all_volume_deltas_valid"] is True
    assert len(res["deltas"]) == 3
    assert res["deltas"][0]["delta_v"] == 10000.0
    assert res["deltas"][1]["delta_v"] == 2500.0
    assert res["deltas"][2]["delta_v"] == -700.0

    # Submerged additive feature (ΔV <= 0) -> SilentMergeError
    silent_merge_steps = [
        {"feature_id": "f1_base", "feature_type": "box", "operation": "new_body", "volume": 10000.0},
        {"feature_id": "f2_submerged", "feature_type": "box", "operation": "join", "volume": 10000.0},
    ]
    with pytest.raises(SilentMergeError):
        verify_volume_deltas(silent_merge_steps, raise_on_error=True)

    # Empty air cut (ΔV == 0) -> NullBooleanCutError
    null_cut_steps = [
        {"feature_id": "f1_base", "feature_type": "box", "operation": "new_body", "volume": 10000.0},
        {"feature_id": "f2_air_cut", "feature_type": "hole", "operation": "cut", "volume": 10000.0},
    ]
    with pytest.raises(NullBooleanCutError):
        verify_volume_deltas(null_cut_steps, raise_on_error=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. 2D Geometric Constraint Solver
# ─────────────────────────────────────────────────────────────────────────────
def test_2d_geometric_constraint_solver():
    r1 = CADIRRectangle(id="plate", width=60.0, height=40.0)
    c1 = CADIRCircle(id="bore", radius=8.0, center=Point3D(x=15.0, y=10.0, z=0.0))

    sketch = CADIRSketchProfile(
        id="test_profile",
        entities=[r1, c1],
        constraints=[
            CADIRConstraint(constraint_type="fixed", entities=["plate"], value=0.0),
            CADIRConstraint(constraint_type="concentric", entities=["bore", "plate"]),
            CADIRConstraint(constraint_type="radius", entities=["bore"], value=12.5),
        ]
    )

    solved_sketch = solve_sketch_constraints(sketch)
    solved_bore = next(e for e in solved_sketch.entities if e.id == "bore")
    assert abs(solved_bore.center.x - 0.0) < 1e-5
    assert abs(solved_bore.center.y - 0.0) < 1e-5
    assert abs(solved_bore.radius - 12.5) < 1e-5


# ─────────────────────────────────────────────────────────────────────────────
# 5. Multi-View Set-of-Mark (SoM) Visual Critic Node
# ─────────────────────────────────────────────────────────────────────────────
def test_visual_verifier_node_pass_through():
    state = {
        "user_prompt": "100x80x10 mounting plate with 4 corner holes",
        "export_paths": {},
        "execution_result": {"success": True},
    }
    verdict_res = visual_verifier_node(state)
    assert verdict_res["visual_critique"]["visually_aligned"] is True
    assert verdict_res["current_agent"] == "visual_verifier"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Lightweight Macro RAG Index
# ─────────────────────────────────────────────────────────────────────────────
def test_macro_rag_retrieval():
    res = query_macro_rag("heavy duty pipe flange with weld neck and 8 bolt holes", operations=["hole", "pattern"], limit=3)
    assert len(res) > 0
    categories = [r["category"] for r in res]
    assert "flange" in categories

    gear_res = query_macro_rag("involute spur gear module 2 24 teeth", operations=["spur_gear_macro"], limit=2)
    assert len(gear_res) > 0
    assert any("gear" in r["category"] for r in gear_res)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Execution-Guided Best-of-N Candidate Sampling & Parameter Snapping
# ─────────────────────────────────────────────────────────────────────────────
def test_candidate_scoring_and_parameter_snapping():
    # Parameter Snapping
    doc = CADIRDocument(
        id="test_snap_doc",
        name="Unsnapped Doc",
        features=[
            CADIRFeature(id="f1", feature_type="box", length=100.0, width=50.0, height=9.8, operation="new_body"),
            CADIRFeature(id="f2", feature_type="hole", diameter=6.55, depth=15.0, operation="cut"),
            CADIRFeature(id="f3", feature_type="hole", diameter=8.92, depth=15.0, operation="cut"),
        ]
    )

    snapped = snap_cadir_parameters(doc)
    # 9.8 should snap to standard stock thickness 10.0
    assert snapped.features[0].height == 10.0
    # 6.55 should snap to standard clearance drill 6.6
    assert snapped.features[1].diameter == 6.6
    assert snapped.features[1].radius == 3.3
    # 8.92 should snap to standard clearance drill 9.0
    assert snapped.features[2].diameter == 9.0
    assert snapped.features[2].radius == 4.5

    # Deterministic Candidate Scoring
    cand_perfect = {
        "is_watertight": True,
        "step_volumes": [
            {"feature_id": "f1", "feature_type": "box", "operation": "new_body", "volume": 1000.0},
            {"feature_id": "f2", "feature_type": "hole", "operation": "cut", "volume": 900.0},
        ],
        "bounding_box": {"xmin": -50, "xmax": 50, "ymin": -25, "ymax": 25, "zmin": 0, "zmax": 10},
    }
    score = score_cadir_candidate(cand_perfect, target_envelope=[100.0, 50.0, 10.0], dfm_warnings_count=0)
    assert score == 150.0
