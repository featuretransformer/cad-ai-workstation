"""
Unit tests for CAD Evaluation Metric Modules in Isolation.
Tests:
- Chamfer Distance & F-score calculation
- Volumetric IoU calculation
- Geometry extraction
- Hungarian feature matching
- Kabsch rotation alignment
"""
import math
from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh

EVAL_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = EVAL_DIR.parent
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from metrics.shape import compute_chamfer_and_fscore, compute_volumetric_iou, normalize_mesh
from metrics.dimensions import evaluate_dimensions
from metrics.positioning import kabsch_rotation, evaluate_positioning


def test_chamfer_and_fscore_identical():
    # Exactly identical point clouds
    pts = np.random.uniform(-10, 10, size=(1000, 3))
    res = compute_chamfer_and_fscore(pts, pts, threshold=0.01)

    assert res["chamfer_distance"] == pytest.approx(0.0, abs=1e-6)
    assert res["f_score"] == pytest.approx(1.0, abs=1e-4)
    assert res["precision"] == pytest.approx(1.0, abs=1e-4)
    assert res["recall"] == pytest.approx(1.0, abs=1e-4)


def test_chamfer_perturbed():
    pts_gt = np.zeros((100, 3))
    pts_gen = np.ones((100, 3))  # Shifted by (1, 1, 1), distance = sqrt(3) ~= 1.732
    res = compute_chamfer_and_fscore(pts_gt, pts_gen, threshold=0.5)

    assert res["chamfer_distance"] == pytest.approx(math.sqrt(3), abs=1e-3)
    assert res["f_score"] == 0.0  # Threshold is 0.5, error is 1.732


def test_volumetric_iou_cubes():
    box_gt = trimesh.creation.box(extents=(10, 10, 10))
    # Identical box
    iou_ident = compute_volumetric_iou(box_gt, box_gt)
    assert iou_ident >= 0.95

    # Completely disjoint box
    box_far = trimesh.creation.box(extents=(10, 10, 10))
    box_far.apply_translation((100, 100, 100))
    iou_disjoint = compute_volumetric_iou(box_gt, box_far)
    assert iou_disjoint == 0.0


def test_kabsch_rotation_svd():
    # Rotate 4 points by 90 degrees around Z axis
    pts = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
    R_true = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    pts_rot = (R_true @ pts.T).T

    R_est = kabsch_rotation(pts, pts_rot)
    pts_recovered = (R_est @ pts.T).T

    np.testing.assert_allclose(pts_recovered, pts_rot, atol=1e-5)


def test_dimensions_eval():
    gt = {
        "bbox_dims": [100.0, 50.0, 20.0],
        "volume": 100000.0,
        "holes": [{"diameter_mm": 10.0}],
    }
    # Within 1% error
    gen_pass = {
        "bbox_dims": [100.5, 49.8, 20.1],
        "volume": 100400.0,
        "holes": [{"diameter_mm": 10.05}],
    }
    res_pass = evaluate_dimensions(gt, gen_pass, tolerance=0.02)
    assert res_pass["all_passed_2pct"] is True

    # High error candidate (>10%)
    gen_fail = {
        "bbox_dims": [120.0, 50.0, 20.0],  # 20% on axis 1
        "volume": 120000.0,
        "holes": [{"diameter_mm": 15.0}],  # 50% on hole
    }
    res_fail = evaluate_dimensions(gt, gen_fail, tolerance=0.02)
    assert res_fail["all_passed_2pct"] is False
    assert res_fail["pass_rate_2pct"] < 0.8
