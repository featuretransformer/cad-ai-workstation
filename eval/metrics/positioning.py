"""
Positioning and Orientation Metrics.
- Feature-centre Euclidean error in mm via Hungarian matching (scipy.optimize.linear_sum_assignment)
- Hole count exact match
- Bounding origin and centroid alignment
- Axis-Alignment Diagnostic: Tests whether positional errors vanish under optimal 3D rigid rotation (Kabsch SVD).
"""
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from scipy.optimize import linear_sum_assignment


def kabsch_rotation(P: np.ndarray, Q: np.ndarray) -> np.ndarray:
    """
    Finds optimal 3D rotation matrix R such that R @ P ~ Q using Kabsch algorithm (SVD).
    P: (N, 3), Q: (N, 3) (already centred).
    """
    if len(P) < 2 or len(Q) < 2:
        return np.eye(3)

    H = P.T @ Q
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T

    # Ensure right-handed coordinate frame (det(R) == +1, not a reflection)
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T

    return R


def evaluate_positioning(
    gt_features: Dict[str, Any],
    gen_features: Dict[str, Any],
    max_position_bar_mm: float = 1.0,
) -> Dict[str, Any]:
    """
    Evaluates placement, origin, and feature positioning.
    Computes:
        1. Centroid offset in mm (world coordinates)
        2. Exact hole count match
        3. Feature-centre errors in mm for matched hole pairs (Hungarian algorithm)
        4. Axis-alignment diagnostic: tests whether positional errors vanish after optimal 3D rotation
    """
    gt_centroid = np.array(gt_features.get("centroid", [0.0, 0.0, 0.0]), dtype=float)
    gen_centroid = np.array(gen_features.get("centroid", [0.0, 0.0, 0.0]), dtype=float)

    centroid_dist_mm = float(np.linalg.norm(gen_centroid - gt_centroid))

    # Hole matching
    gt_holes = gt_features.get("holes", [])
    gen_holes = gen_features.get("holes", [])

    gt_hole_count = len(gt_holes)
    gen_hole_count = len(gen_holes)
    hole_count_match = (gt_hole_count == gen_hole_count)

    hole_errors_mm: List[float] = []
    aligned_hole_errors_mm: List[float] = []
    rotation_diagnostic = {
        "rotational_misalignment_detected": False,
        "raw_mean_error_mm": 0.0,
        "aligned_mean_error_mm": 0.0,
        "error_reduction_pct": 0.0,
    }

    if gt_holes and gen_holes:
        gt_centres = np.array([h["center"] for h in gt_holes], dtype=float)
        gen_centres = np.array([h["center"] for h in gen_holes], dtype=float)

        # Distance cost matrix between all GT and Generated holes
        # C[i, j] = ||gt_centres[i] - gen_centres[j]||
        diff = gt_centres[:, None, :] - gen_centres[None, :, :]
        cost_matrix = np.linalg.norm(diff, axis=-1)

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        matched_gt = []
        matched_gen = []
        for r, c in zip(row_ind, col_ind):
            err = float(cost_matrix[r, c])
            hole_errors_mm.append(round(err, 3))
            matched_gt.append(gt_centres[r])
            matched_gen.append(gen_centres[c])

        # Missing holes get penalized
        missing_count = max(0, gt_hole_count - len(row_ind))
        for _ in range(missing_count):
            hole_errors_mm.append(50.0)  # Standard penalty for missing feature

        # Axis-alignment diagnostic (Kabsch rotation on matched centers)
        if len(matched_gt) >= 2:
            m_gt = np.array(matched_gt)
            m_gen = np.array(matched_gen)

            c_gt = np.mean(m_gt, axis=0)
            c_gen = np.mean(m_gen, axis=0)

            p_gt = m_gt - c_gt
            p_gen = m_gen - c_gen

            R_opt = kabsch_rotation(p_gen, p_gt)
            p_gen_rot = (R_opt @ p_gen.T).T

            aligned_diff = np.linalg.norm(p_gen_rot - p_gt, axis=-1)
            raw_mean = float(np.mean([cost_matrix[r, c] for r, c in zip(row_ind, col_ind)]))
            aligned_mean = float(np.mean(aligned_diff))

            red_pct = ((raw_mean - aligned_mean) / max(raw_mean, 1e-6)) * 100.0 if raw_mean > 0.0 else 0.0
            is_misaligned = (raw_mean > max_position_bar_mm) and (aligned_mean <= max_position_bar_mm)

            rotation_diagnostic = {
                "rotational_misalignment_detected": bool(is_misaligned),
                "raw_mean_error_mm": round(raw_mean, 3),
                "aligned_mean_error_mm": round(aligned_mean, 3),
                "error_reduction_pct": round(red_pct, 1),
            }

    elif gt_holes and not gen_holes:
        # All holes missing
        hole_errors_mm = [50.0] * gt_hole_count

    mean_hole_err = float(np.mean(hole_errors_mm)) if hole_errors_mm else 0.0
    max_hole_err = float(np.max(hole_errors_mm)) if hole_errors_mm else 0.0

    position_pass = bool(
        centroid_dist_mm <= max_position_bar_mm
        and (mean_hole_err <= max_position_bar_mm if gt_holes else True)
    )

    return {
        "hole_count_match": hole_count_match,
        "gt_hole_count": gt_hole_count,
        "gen_hole_count": gen_hole_count,
        "centroid_dist_mm": round(centroid_dist_mm, 3),
        "mean_feature_pos_error_mm": round(mean_hole_err, 3),
        "max_feature_pos_error_mm": round(max_hole_err, 3),
        "position_pass_1mm": position_pass,
        "hole_position_errors_mm": hole_errors_mm,
        "axis_alignment_diagnostic": rotation_diagnostic,
    }
