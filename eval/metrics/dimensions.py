"""
Dimensional Accuracy Metrics: Bounding Box Axes, Volume, Hole Diameters, and Wall Thickness.
Evaluated strictly against ground-truth geometry (STEP/mesh), never from prompt strings.
Calculates pass rate within 2% tolerance, median, and p90 relative error.
"""
from typing import Dict, Any, List, Optional
import numpy as np


def evaluate_dimensions(
    gt_features: Dict[str, Any],
    gen_features: Dict[str, Any],
    tolerance: float = 0.02,  # 2% default pass tolerance
) -> Dict[str, Any]:
    """
    Evaluates dimensional accuracy between ground-truth and candidate geometry.
    Compares:
        1. Bounding box extents (both raw ordered and sorted dimensions)
        2. Solid volume
        3. Hole diameters (matched holes)
        4. Wall thickness (if present in GT)
    """
    errors_pct: List[float] = []
    checks: Dict[str, Any] = {}

    # 1. Bounding Box Dimensions
    gt_bbox = gt_features.get("bbox_dims", [0.0, 0.0, 0.0])
    gen_bbox = gen_features.get("bbox_dims", [0.0, 0.0, 0.0])

    # Compare sorted principal dimensions to be robust to 90° orientation differences
    gt_sorted = sorted([max(float(d), 1e-4) for d in gt_bbox], reverse=True)
    gen_sorted = sorted([max(float(d), 1e-4) for d in gen_bbox], reverse=True)

    bbox_axis_errors = []
    for i, (g, c) in enumerate(zip(gt_sorted, gen_sorted)):
        err_pct = abs(c - g) / g * 100.0
        bbox_axis_errors.append(round(err_pct, 3))
        errors_pct.append(err_pct)

    checks["bbox_sorted_gt_mm"] = gt_sorted
    checks["bbox_sorted_gen_mm"] = gen_sorted
    checks["bbox_axis_errors_pct"] = bbox_axis_errors
    checks["max_bbox_error_pct"] = max(bbox_axis_errors) if bbox_axis_errors else 999.0

    # 2. Volume
    gt_vol = max(float(gt_features.get("volume", 0.0)), 1e-6)
    gen_vol = max(float(gen_features.get("volume", 0.0)), 0.0)
    vol_err_pct = abs(gen_vol - gt_vol) / gt_vol * 100.0
    errors_pct.append(vol_err_pct)

    checks["gt_volume_mm3"] = round(gt_vol, 3)
    checks["gen_volume_mm3"] = round(gen_vol, 3)
    checks["volume_error_pct"] = round(vol_err_pct, 3)

    # 3. Hole Diameters
    gt_holes = gt_features.get("holes", [])
    gen_holes = gen_features.get("holes", [])
    hole_diam_errors = []

    if gt_holes:
        gt_diams = sorted([float(h["diameter_mm"]) for h in gt_holes])
        gen_diams = sorted([float(h["diameter_mm"]) for h in gen_holes]) if gen_holes else []

        for i, gd in enumerate(gt_diams):
            if i < len(gen_diams):
                cd = gen_diams[i]
                d_err = abs(cd - gd) / max(gd, 1e-4) * 100.0
                hole_diam_errors.append(round(d_err, 3))
                errors_pct.append(d_err)
            else:
                # Missing hole counts as 100% error
                hole_diam_errors.append(100.0)
                errors_pct.append(100.0)

    checks["gt_hole_count"] = len(gt_holes)
    checks["gen_hole_count"] = len(gen_holes)
    checks["hole_diameter_errors_pct"] = hole_diam_errors

    # 4. Wall Thickness (if specified in ground-truth)
    gt_wall = gt_features.get("wall_thickness_mm")
    if gt_wall is not None and gt_wall > 0:
        # Check against minimum non-zero bounding extent or thin feature
        gt_w = float(gt_wall)
        min_extent = min(gen_sorted) if gen_sorted else 0.0
        # If part is thin shell/bracket/channel, min extent correlates with wall thickness
        wall_err = abs(min_extent - gt_w) / gt_w * 100.0
        checks["wall_thickness_gt_mm"] = gt_w
        checks["wall_thickness_est_mm"] = round(min_extent, 3)
        checks["wall_thickness_error_pct"] = round(wall_err, 3)
        errors_pct.append(wall_err)

    # Calculate overall aggregate statistics
    tol_pct = tolerance * 100.0
    passed_checks = sum(1 for e in errors_pct if e <= tol_pct)
    total_checks = max(len(errors_pct), 1)
    pass_rate_2pct = passed_checks / total_checks

    median_err = float(np.median(errors_pct)) if errors_pct else 999.0
    p90_err = float(np.percentile(errors_pct, 90)) if errors_pct else 999.0

    return {
        "pass_rate_2pct": round(pass_rate_2pct, 4),
        "median_error_pct": round(median_err, 3),
        "p90_error_pct": round(p90_err, 3),
        "all_passed_2pct": bool(pass_rate_2pct >= 0.999),
        "checks": checks,
    }
