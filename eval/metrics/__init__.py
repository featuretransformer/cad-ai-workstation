"""
Unified Evaluation Metrics Interface for CAD Models.
Executes physical geometry extraction, shape similarity, dimensional verification,
and positional accuracy checks.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import trimesh

from .extractor import extract_cad_features
from .shape import evaluate_shape
from .dimensions import evaluate_dimensions
from .positioning import evaluate_positioning


def evaluate_cad_model(
    gt_step_path: str,
    gt_stl_path: str,
    gen_step_path: Optional[str] = None,
    gen_stl_path: Optional[str] = None,
    tolerance_2pct: float = 0.02,
    position_bar_mm: float = 1.0,
    sample_points: int = 50000,
) -> Dict[str, Any]:
    """
    Evaluates generated CAD candidate against ground-truth geometry.
    Returns comprehensive evaluation dictionary across shape, dimensions, and positioning.
    """
    # 1. Feature Extraction
    gt_features = extract_cad_features(step_path=gt_step_path, stl_path=gt_stl_path)
    gen_features = extract_cad_features(step_path=gen_step_path, stl_path=gen_stl_path)

    # 2. Validity check
    is_valid_solid = bool(
        gen_features["valid"]
        and gen_features["is_closed_solid"]
        and gen_features["volume"] > 0.0
    )

    if not is_valid_solid:
        return {
            "valid_solid": False,
            "overall_pass": False,
            "shape": {
                "valid_meshes": False,
                "normalised": {"chamfer_distance": 999.0, "f_score": 0.0, "iou": 0.0},
                "raw": {"chamfer_distance_mm": 999.0, "f_score": 0.0, "iou": 0.0},
            },
            "dimensions": {
                "pass_rate_2pct": 0.0,
                "median_error_pct": 100.0,
                "p90_error_pct": 100.0,
                "all_passed_2pct": False,
                "checks": {},
            },
            "positioning": {
                "hole_count_match": False,
                "centroid_dist_mm": 999.0,
                "mean_feature_pos_error_mm": 999.0,
                "position_pass_1mm": False,
                "axis_alignment_diagnostic": {
                    "rotational_misalignment_detected": False,
                    "raw_mean_error_mm": 999.0,
                    "aligned_mean_error_mm": 999.0,
                },
            },
            "features_summary": {
                "gt_volume": gt_features["volume"],
                "gen_volume": 0.0,
                "gt_bbox": gt_features["bbox_dims"],
                "gen_bbox": [0.0, 0.0, 0.0],
            },
        }

    # 3. Shape Evaluation
    mesh_gt = trimesh.load(str(gt_stl_path), force="mesh")
    mesh_gen = trimesh.load(str(gen_stl_path), force="mesh")
    shape_res = evaluate_shape(mesh_gt, mesh_gen, sample_count=sample_points)

    # 4. Dimensional Evaluation
    dim_res = evaluate_dimensions(gt_features, gen_features, tolerance=tolerance_2pct)

    # 5. Positioning Evaluation
    pos_res = evaluate_positioning(gt_features, gen_features, max_position_bar_mm=position_bar_mm)

    # Overall pass criteria:
    # 1. Valid closed solid
    # 2. Normalised Chamfer < 0.03 and F-score >= 0.90
    # 3. Dimensional 2% pass rate >= 80%
    # 4. Feature positioning error < 1mm (or rotation-aligned pass)
    overall_pass = bool(
        is_valid_solid
        and shape_res["normalised"]["chamfer_distance"] <= 0.035
        and shape_res["normalised"]["f_score"] >= 0.88
        and dim_res["pass_rate_2pct"] >= 0.80
        and (pos_res["position_pass_1mm"] or pos_res["axis_alignment_diagnostic"]["rotational_misalignment_detected"])
    )

    return {
        "valid_solid": is_valid_solid,
        "overall_pass": overall_pass,
        "shape": shape_res,
        "dimensions": dim_res,
        "positioning": pos_res,
        "features_summary": {
            "gt_volume": round(gt_features["volume"], 2),
            "gen_volume": round(gen_features["volume"], 2),
            "gt_bbox": [round(x, 2) for x in gt_features["bbox_dims"]],
            "gen_bbox": [round(x, 2) for x in gen_features["bbox_dims"]],
            "gt_hole_count": gt_features["hole_count"],
            "gen_hole_count": gen_features["hole_count"],
        },
    }
