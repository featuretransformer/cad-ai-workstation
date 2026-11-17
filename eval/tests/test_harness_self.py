"""
Harness Self-Tests.
Verifies the integrity of the evaluation harness before real runs:
1. Ground truth fed in as the "model output" must score 100% across all metrics.
2. Deliberately mutated/broken models must FAIL their targeted metrics:
   - Wrong hole diameter -> fails dimensional hole check
   - Shifted hole -> fails feature position check (>1 mm error)
   - Missing hole -> fails hole count exact match
   - Scaled part -> fails raw Chamfer and dimensional checks
   - Rotated part -> triggers axis alignment diagnostic (rotational misalignment)
"""
from pathlib import Path
import sys
import pytest
from build123d import *

EVAL_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = EVAL_DIR.parent
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from metrics import evaluate_cad_model

TMP_MUTANTS_DIR = EVAL_DIR / "tests" / "mutants"
TMP_MUTANTS_DIR.mkdir(parents=True, exist_ok=True)

GOLDEN_STEP_DIR = EVAL_DIR / "golden_set" / "step"


@pytest.fixture(scope="module")
def plate_ground_truth():
    """Ground truth reference: 80x50x8 mm plate with a centered 20 mm through-hole (G011)."""
    step_file = GOLDEN_STEP_DIR / "G011.step"
    stl_file = GOLDEN_STEP_DIR / "G011.stl"
    assert step_file.exists() and stl_file.exists(), "Golden set G011 not found — run build_golden_set.py first!"
    return str(step_file), str(stl_file)


# ─── Self-Test 1: Identity Test (GT as Model Output) ─────────────────────────

def test_ground_truth_scores_100_percent(plate_ground_truth):
    """Ground truth fed as candidate model output must score 100% on every metric."""
    gt_step, gt_stl = plate_ground_truth
    res = evaluate_cad_model(gt_step, gt_stl, gt_step, gt_stl)

    assert res["valid_solid"] is True
    assert res["overall_pass"] is True

    # Shape metrics (stochastic sampling across 50k points yields sampling noise ~0.002)
    assert res["shape"]["normalised"]["chamfer_distance"] < 0.005
    assert res["shape"]["normalised"]["f_score"] == pytest.approx(1.0, abs=1e-3)
    assert res["shape"]["normalised"]["iou"] >= 0.98

    # Dimensional metrics
    assert res["dimensions"]["pass_rate_2pct"] == 1.0
    assert res["dimensions"]["all_passed_2pct"] is True
    assert res["dimensions"]["median_error_pct"] < 0.05

    # Positioning metrics
    assert res["positioning"]["hole_count_match"] is True
    assert res["positioning"]["position_pass_1mm"] is True
    assert res["positioning"]["mean_feature_pos_error_mm"] == pytest.approx(0.0, abs=1e-3)


# ─── Self-Test 2: Scaled Part Mutant ──────────────────────────────────────────

def test_mutant_scaled_part_fails_dimensions_and_raw_shape(plate_ground_truth):
    """Mutant scaled by 1.25x must fail dimensional 2% check and raw shape."""
    gt_step, gt_stl = plate_ground_truth

    # Create 1.25x scaled mutant: 100x62.5x10 mm plate with 25 mm hole
    with BuildPart() as p:
        Box(100.0, 62.5, 10.0)
        Cylinder(radius=12.5, height=10.0, mode=Mode.SUBTRACT)

    mut_step = TMP_MUTANTS_DIR / "mutant_scaled.step"
    mut_stl = TMP_MUTANTS_DIR / "mutant_scaled.stl"
    export_step(p.part, str(mut_step))
    export_stl(p.part, str(mut_stl))

    res = evaluate_cad_model(gt_step, gt_stl, str(mut_step), str(mut_stl))

    # Must fail dimensional 2% check
    assert res["dimensions"]["all_passed_2pct"] is False
    assert res["dimensions"]["pass_rate_2pct"] < 0.5
    assert res["dimensions"]["checks"]["volume_error_pct"] > 80.0  # 1.25^3 - 1 ~ 95% error
    # Must fail raw Chamfer distance (>2 mm)
    assert res["shape"]["raw"]["chamfer_distance_mm"] > 2.0


# ─── Self-Test 3: Shifted Hole Mutant ─────────────────────────────────────────

def test_mutant_shifted_hole_fails_positioning(plate_ground_truth):
    """Mutant with hole center shifted by 8 mm along X must fail 1 mm position check."""
    gt_step, gt_stl = plate_ground_truth

    # Create plate with shifted hole at (x=8, y=0)
    with BuildPart() as p:
        Box(80.0, 50.0, 8.0)
        with Locations((8.0, 0.0, 0.0)):
            Cylinder(radius=10.0, height=8.0, mode=Mode.SUBTRACT)

    mut_step = TMP_MUTANTS_DIR / "mutant_shifted.step"
    mut_stl = TMP_MUTANTS_DIR / "mutant_shifted.stl"
    export_step(p.part, str(mut_step))
    export_stl(p.part, str(mut_stl))

    res = evaluate_cad_model(gt_step, gt_stl, str(mut_step), str(mut_stl))

    # Dimensions are identical
    assert res["dimensions"]["all_passed_2pct"] is True
    # But positioning must fail 1 mm tolerance
    assert res["positioning"]["position_pass_1mm"] is False
    assert res["positioning"]["mean_feature_pos_error_mm"] == pytest.approx(8.0, abs=0.5)


# ─── Self-Test 4: Wrong Hole Diameter Mutant ──────────────────────────────────

def test_mutant_wrong_hole_diameter_fails_hole_dimension(plate_ground_truth):
    """Mutant with 12 mm hole instead of 20 mm hole must fail hole diameter check."""
    gt_step, gt_stl = plate_ground_truth

    # 12 mm hole (40% error)
    with BuildPart() as p:
        Box(80.0, 50.0, 8.0)
        Cylinder(radius=6.0, height=8.0, mode=Mode.SUBTRACT)

    mut_step = TMP_MUTANTS_DIR / "mutant_wrong_hole_diam.step"
    mut_stl = TMP_MUTANTS_DIR / "mutant_wrong_hole_diam.stl"
    export_step(p.part, str(mut_step))
    export_stl(p.part, str(mut_stl))

    res = evaluate_cad_model(gt_step, gt_stl, str(mut_step), str(mut_stl))

    assert res["dimensions"]["all_passed_2pct"] is False
    assert res["dimensions"]["checks"]["hole_diameter_errors_pct"][0] == pytest.approx(40.0, abs=1.0)


# ─── Self-Test 5: Missing Hole Mutant ─────────────────────────────────────────

def test_mutant_missing_hole_fails_hole_count(plate_ground_truth):
    """Mutant without any hole must fail hole_count_match."""
    gt_step, gt_stl = plate_ground_truth

    # Solid block without hole
    with BuildPart() as p:
        Box(80.0, 50.0, 8.0)

    mut_step = TMP_MUTANTS_DIR / "mutant_missing_hole.step"
    mut_stl = TMP_MUTANTS_DIR / "mutant_missing_hole.stl"
    export_step(p.part, str(mut_step))
    export_stl(p.part, str(mut_stl))

    res = evaluate_cad_model(gt_step, gt_stl, str(mut_step), str(mut_stl))

    assert res["positioning"]["hole_count_match"] is False
    assert res["positioning"]["gen_hole_count"] == 0
    assert res["positioning"]["gt_hole_count"] == 1


# ─── Self-Test 6: Rotated Part Mutant (Axis Alignment Diagnostic) ─────────────

def test_mutant_rotated_part_triggers_alignment_diagnostic(plate_ground_truth):
    """
    Mutant with 2 offset holes rotated 90 degrees around Z axis.
    Un-aligned positioning error will be large, but rotation alignment diagnostic
    must detect rotational misalignment and show errors vanish after alignment.
    """
    # Create reference plate with 2 holes: at (-20, 0) and (+20, 0)
    with BuildPart() as p_ref:
        Box(80.0, 50.0, 8.0)
        with Locations((-20.0, 0.0, 0.0), (20.0, 0.0, 0.0)):
            Cylinder(radius=5.0, height=8.0, mode=Mode.SUBTRACT)

    ref_step = TMP_MUTANTS_DIR / "ref_two_holes.step"
    ref_stl = TMP_MUTANTS_DIR / "ref_two_holes.stl"
    export_step(p_ref.part, str(ref_step))
    export_stl(p_ref.part, str(ref_stl))

    # Create rotated version: 90 deg around Z -> holes at (0, -20) and (0, +20)
    with BuildPart() as p_rot:
        with Locations(Rotation(0, 0, 90)):
            Box(80.0, 50.0, 8.0)
            with Locations((-20.0, 0.0, 0.0), (20.0, 0.0, 0.0)):
                Cylinder(radius=5.0, height=8.0, mode=Mode.SUBTRACT)

    rot_step = TMP_MUTANTS_DIR / "mutant_rotated_90.step"
    rot_stl = TMP_MUTANTS_DIR / "mutant_rotated_90.stl"
    export_step(p_rot.part, str(rot_step))
    export_stl(p_rot.part, str(rot_stl))

    res = evaluate_cad_model(str(ref_step), str(ref_stl), str(rot_step), str(rot_stl))

    # Raw hole error should be ~28.28 mm (distance from (20, 0) to (0, 20))
    diag = res["positioning"]["axis_alignment_diagnostic"]
    assert diag["raw_mean_error_mm"] > 20.0
    # But after Kabsch rotation, aligned error should vanish (< 0.5 mm)
    assert diag["aligned_mean_error_mm"] < 0.5
    assert diag["rotational_misalignment_detected"] is True
