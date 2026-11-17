"""
Phase P0 Reliability & Deterministic Core Test Suite.
Validates:
1. AgentCAD-style 7-layer OpenCASCADE B-rep validation engine (brep_validator.py).
2. MAC-style CADBrief pre-execution contract & VerificationTarget generation (brief_schema.py, supervisor.py).
3. Independent QA Critic / Judge node arbitration (ACCEPT | REPAIR | HALT) (validator_nodes.py:qa_judge_node).
4. Localized in-place CADIR AST diff repair engine without sibling mutation (cadir_repair_agent.py).
"""
import pytest
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.brep_validator import run_opencascade_validation
from cad.brief_schema import (
    build_cad_brief,
    create_verification_receipt,
    VerificationTarget,
    JudgeDecision,
)
from agents.supervisor import supervisor_node
from agents.validator_nodes import geometry_validator_node, qa_judge_node
from agents.cadir_repair_agent import cadir_repair_node
from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    Vector3D,
    Point3D,
)


class TestP0_1_OpenCASCADE7LayerValidator:
    """Tests for the 7-Layer OpenCASCADE Validation Engine."""

    def test_7layer_validation_on_golden_step(self):
        step_path = Path(__file__).resolve().parent.parent / "eval" / "golden_set" / "step" / "G001.step"
        if not step_path.exists():
            pytest.skip("G001.step golden file not found")

        res = run_opencascade_validation(str(step_path))
        assert res["is_valid"] is True, f"Validation failed: {res.get('errors')}"
        assert res["first_failure"] is None
        layers = res["layers"]

        # Assert all 7 layers executed
        assert "file_parse" in layers
        assert layers["file_parse"]["status"] == "pass"

        assert "kernel_load" in layers
        assert layers["kernel_load"]["status"] == "pass"

        assert "brep_check" in layers
        assert layers["brep_check"]["status"] == "pass"
        assert layers["brep_check"]["is_valid"] is True

        assert "shell_closure" in layers
        assert layers["shell_closure"]["status"] == "pass"
        assert layers["shell_closure"]["open_shell_count"] == 0

        assert "mesh_manifold" in layers
        assert layers["mesh_manifold"]["status"] == "pass"

        assert "structure" in layers
        assert layers["structure"]["status"] == "pass"
        assert layers["structure"]["solid_count"] == 1
        assert layers["structure"]["edge_count"] > 0

        assert "advisory" in layers
        assert layers["advisory"]["status"] == "pass"

    def test_7layer_validation_on_corrupt_step(self, tmp_path):
        bad_file = tmp_path / "corrupt.step"
        bad_file.write_text("ISO-10303-21; HEADER; CORRUPTED JUNK DATA ENDSEC; END-ISO-10303-21;")

        res = run_opencascade_validation(str(bad_file))
        assert res["is_valid"] is False
        assert len(res["errors"]) > 0
        assert res["first_failure"] in ("file_parse", "kernel_load", "brep_check")


class TestP0_2_CADBriefAndVerificationTargets:
    """Tests for CADBrief & Machine-Measurable Verification Targets."""

    def test_brief_generation_from_engineering_prompt(self):
        prompt = "Create a 120x80x15mm aluminum mounting bracket with 30mm central bore, M6 clearance holes, and 60mm PCD"
        brief = build_cad_brief(
            prompt=prompt,
            parsed_intent={"component_family": "bracket"},
            sem_dims={
                "box": {"length": 120.0, "width": 80.0, "height": 15.0},
                "bore": {"diameter": 30.0, "radius": 15.0},
                "hole_diameter": 6.6,
                "pcd": {"diameter": 60.0, "radius": 30.0},
            },
        )

        assert brief.part_category == "bracket"
        assert brief.bounding_box_envelope == [120.0, 80.0, 15.0]

        target_ids = [t.id for t in brief.verification_targets]
        assert "target-single-body" in target_ids
        assert "target-watertight" in target_ids
        assert "target-overall-x" in target_ids
        assert "target-overall-y" in target_ids
        assert "target-overall-z" in target_ids
        assert "target-central-bore" in target_ids
        assert "target-hole-diameter" in target_ids
        assert "target-pcd" in target_ids

        # Check critical invariants
        single_body = next(t for t in brief.verification_targets if t.id == "target-single-body")
        assert single_body.critical is True
        assert single_body.nominal == 1.0

        watertight = next(t for t in brief.verification_targets if t.id == "target-watertight")
        assert watertight.critical is True

    def test_supervisor_node_attaches_brief_and_targets(self):
        state = {
            "user_prompt": "100x100x20mm steel block with 40mm bore",
            "parsed_intent": {},
        }
        res = supervisor_node(state)
        assert "cad_brief" in res
        assert "verification_targets" in res
        assert len(res["verification_targets"]) >= 4
        assert any(t["id"] == "target-overall-x" for t in res["verification_targets"])

    def test_verification_receipt_generation(self):
        targets = [
            VerificationTarget(id="target-single-body", kind="single_body", nominal=1.0, critical=True),
            VerificationTarget(id="target-overall-x", kind="overall_dimension", measurement_axis="x", nominal=100.0, tolerance_upper=1.0, tolerance_lower=1.0),
        ]
        exec_res = {
            "success": True,
            "volume": 160000.0,
            "bounding_box": {"xmin": -50.0, "xmax": 50.0, "ymin": -40.0, "ymax": 40.0, "zmin": -10.0, "zmax": 10.0},
        }
        step_res = {
            "valid": True,
            "layers": {"brep_check": {"solid_count": 1}, "shell_closure": {"is_closed": True}},
            "errors": [],
            "warnings": [],
        }

        receipt = create_verification_receipt(targets, exec_res, step_res=step_res)
        assert receipt.is_valid is True
        assert len(receipt.target_results) == 2
        assert all(tr.passed for tr in receipt.target_results)


class TestP0_3_QAJudgeNode:
    """Tests for Independent QA Critic / Judge Arbitration Node."""

    def test_qa_judge_accepts_clean_model(self):
        state = {
            "geometry_valid": True,
            "validation_errors": [],
            "visual_critique": {"visually_aligned": True},
            "repair_attempts": 0,
            "verification_receipt": {
                "is_valid": True,
                "target_results": [
                    {"target_id": "target-single-body", "passed": True, "critical": True},
                    {"target_id": "target-overall-x", "passed": True, "critical": False},
                ],
            },
        }
        res = qa_judge_node(state)
        dec = res["judge_decision"]
        assert dec["action"] == "accept"
        assert "satisfied" in dec["reason"].lower()

    def test_qa_judge_repairs_fixable_defect_and_targets_feature(self):
        doc = CADIRDocument(
            id="test_part",
            component_family="bracket",
            features=[
                CADIRFeature(id="feat_box_1", feature_type="box", length=80.0, width=80.0, height=20.0, operation="new_body"),
                CADIRFeature(id="feat_bore_1", feature_type="hole", diameter=15.0, radius=7.5, operation="cut"),
            ],
        )
        state = {
            "geometry_valid": False,
            "validation_errors": ["Bore diameter out of spec"],
            "visual_critique": {"visually_aligned": True},
            "repair_attempts": 0,
            "max_retries": 3,
            "cadir_document": doc,
            "verification_receipt": {
                "is_valid": False,
                "target_results": [
                    {"target_id": "target-central-bore", "kind": "hole_diameter", "nominal": 25.0, "passed": False, "critical": False},
                ],
            },
        }
        res = qa_judge_node(state)
        dec = res["judge_decision"]
        assert dec["action"] == "repair"
        assert dec["targeted_feature_id"] == "feat_bore_1"
        assert dec["suggested_patch"]["nominal"] == 25.0

    def test_qa_judge_halts_on_persistent_execution_failure(self):
        state = {
            "geometry_valid": False,
            "execution_result": {"success": False, "error": "Fatal OpenCASCADE topology fault"},
            "repair_attempts": 3,
            "max_retries": 3,
            "verification_receipt": {"target_results": []},
        }
        res = qa_judge_node(state)
        dec = res["judge_decision"]
        assert dec["action"] == "halt"


class TestP0_4_InPlaceCADIRASTDiffRepair:
    """Tests for localized in-place AST diff repair without sibling feature mutation."""

    def test_in_place_repair_mutates_only_targeted_feature(self):
        base_box = CADIRFeature(id="feat_base", feature_type="box", length=100.0, width=80.0, height=20.0, operation="new_body")
        bore_hole = CADIRFeature(id="feat_bore", feature_type="hole", diameter=15.0, radius=7.5, depth=30.0, operation="cut")
        fillet = CADIRFeature(id="feat_fillet", feature_type="fillet", radius=3.0)

        doc = CADIRDocument(
            id="test_part",
            component_family="plate",
            features=[base_box, bore_hole, fillet],
        )

        state = {
            "cadir_document": doc,
            "repair_attempts": 0,
            "max_retries": 3,
            "judge_decision": {
                "action": "repair",
                "targeted_feature_id": "feat_bore",
                "failure_targets": ["target-central-bore"],
                "suggested_patch": {
                    "target_id": "target-central-bore",
                    "target_kind": "hole_diameter",
                    "nominal": 35.0,
                },
            },
        }

        res = cadir_repair_node(state)
        repaired_doc: CADIRDocument = res["cadir_document"]

        # Assert targeted feature was updated
        target_f = next(f for f in repaired_doc.features if f.id == "feat_bore")
        assert target_f.diameter == 35.0
        assert target_f.radius == 17.5

        # Assert sibling features remained 100% untouched
        sibling_base = next(f for f in repaired_doc.features if f.id == "feat_base")
        assert sibling_base.length == 100.0
        assert sibling_base.width == 80.0
        assert sibling_base.height == 20.0

        sibling_fillet = next(f for f in repaired_doc.features if f.id == "feat_fillet")
        assert sibling_fillet.radius == 3.0
        assert sibling_fillet.suppressed is False
