"""
Shape Accuracy Metrics: Chamfer Distance, F-Score, and Volumetric IoU.
Supports both Normalised Mode (centred + scaled to unit box) and Raw Mode (world units and placement).
Uses KDTree surface point cloud sampling (10k-100k points).
"""
from typing import Dict, Any, Tuple, Optional
import numpy as np
from scipy.spatial import cKDTree
import trimesh


def normalize_mesh(mesh: trimesh.Trimesh) -> Tuple[trimesh.Trimesh, np.ndarray, float]:
    """
    Centres mesh at origin and isotropically scales it so max bounding box extent is 1.0.
    Returns (normalized_mesh, original_center, scale_factor).
    """
    mesh_copy = mesh.copy()
    bounds = mesh_copy.bounds
    center = (bounds[0] + bounds[1]) / 2.0
    extents = bounds[1] - bounds[0]
    max_extent = max(float(np.max(extents)), 1e-6)

    mesh_copy.apply_translation(-center)
    mesh_copy.apply_scale(1.0 / max_extent)
    return mesh_copy, center, max_extent


def compute_chamfer_and_fscore(
    pts_gt: np.ndarray,
    pts_gen: np.ndarray,
    threshold: float = 0.01,
) -> Dict[str, float]:
    """
    Computes bidirectional Chamfer Distance and Point-Cloud F-Score.
    - Chamfer Distance: Mean Euclidean distance (symmetric average).
    - F-Score at threshold: Harmonic mean of precision (gen -> gt) and recall (gt -> gen).
    """
    tree_gt = cKDTree(pts_gt)
    tree_gen = cKDTree(pts_gen)

    # Distances from generated points to nearest GT point
    dists_gen_to_gt, _ = tree_gt.query(pts_gen, k=1)
    # Distances from GT points to nearest generated point
    dists_gt_to_gen, _ = tree_gen.query(pts_gt, k=1)

    mean_gen_to_gt = float(np.mean(dists_gen_to_gt))
    mean_gt_to_gen = float(np.mean(dists_gt_to_gen))
    chamfer = 0.5 * (mean_gen_to_gt + mean_gt_to_gen)

    # Precision & Recall at threshold
    precision = float(np.mean(dists_gen_to_gt < threshold))
    recall = float(np.mean(dists_gt_to_gen < threshold))

    if precision + recall > 1e-12:
        f_score = 2.0 * (precision * recall) / (precision + recall)
    else:
        f_score = 0.0

    return {
        "chamfer_distance": round(chamfer, 6),
        "chamfer_gt_to_gen": round(mean_gt_to_gen, 6),
        "chamfer_gen_to_gt": round(mean_gen_to_gt, 6),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f_score": round(f_score, 4),
    }


def compute_volumetric_iou(mesh_gt: trimesh.Trimesh, mesh_gen: trimesh.Trimesh, pitch: float = 0.02) -> float:
    """
    Computes Volumetric IoU using 3D voxelization or point-in-mesh containment testing.
    """
    try:
        # Check if meshes are non-empty and have volume
        if mesh_gt.is_empty or mesh_gen.is_empty:
            return 0.0

        # Create combined bounding box query grid
        b_min = np.minimum(mesh_gt.bounds[0], mesh_gen.bounds[0])
        b_max = np.maximum(mesh_gt.bounds[1], mesh_gen.bounds[1])
        diag = np.linalg.norm(b_max - b_min)
        if diag < 1e-6:
            return 0.0

        # Adaptive voxel grid resolution (approx 40^3 to 50^3 grid points = ~64k–125k query points)
        grid_pitch = max(pitch, diag / 45.0)
        xs = np.arange(b_min[0], b_max[0] + grid_pitch, grid_pitch)
        ys = np.arange(b_min[1], b_max[1] + grid_pitch, grid_pitch)
        zs = np.arange(b_min[2], b_max[2] + grid_pitch, grid_pitch)

        # Cap grid size to prevent memory explosion
        if len(xs) * len(ys) * len(zs) > 150000:
            grid_pitch = diag / 35.0
            xs = np.arange(b_min[0], b_max[0] + grid_pitch, grid_pitch)
            ys = np.arange(b_min[1], b_max[1] + grid_pitch, grid_pitch)
            zs = np.arange(b_min[2], b_max[2] + grid_pitch, grid_pitch)

        grid_pts = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), -1).reshape(-1, 3)

        inside_gt = mesh_gt.contains(grid_pts)
        inside_gen = mesh_gen.contains(grid_pts)

        intersection = np.sum(inside_gt & inside_gen)
        union = np.sum(inside_gt | inside_gen)

        if union == 0:
            return 0.0
        return round(float(intersection / union), 4)

    except Exception:
        # Fallback to bounding box overlap IoU if ray containment fails
        try:
            gt_min, gt_max = mesh_gt.bounds[0], mesh_gt.bounds[1]
            gen_min, gen_max = mesh_gen.bounds[0], mesh_gen.bounds[1]

            inter_min = np.maximum(gt_min, gen_min)
            inter_max = np.minimum(gt_max, gen_max)
            inter_dims = np.maximum(0.0, inter_max - inter_min)
            inter_vol = float(np.prod(inter_dims))

            vol_gt = float(np.prod(gt_max - gt_min))
            vol_gen = float(np.prod(gen_max - gen_min))
            union_vol = vol_gt + vol_gen - inter_vol

            if union_vol <= 1e-9:
                return 0.0
            return round(inter_vol / union_vol, 4)
        except Exception:
            return 0.0


def evaluate_shape(
    mesh_gt: trimesh.Trimesh,
    mesh_gen: trimesh.Trimesh,
    sample_count: int = 50000,
    norm_threshold: float = 0.01,
    raw_threshold_mm: float = 1.0,
) -> Dict[str, Any]:
    """
    Evaluates shape similarity between Ground-Truth and Generated meshes in both
    Normalised mode and Raw mode.
    """
    if mesh_gt is None or mesh_gen is None or mesh_gt.is_empty or mesh_gen.is_empty:
        return {
            "valid_meshes": False,
            "normalised": {
                "chamfer_distance": 999.0,
                "f_score": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "iou": 0.0,
            },
            "raw": {
                "chamfer_distance_mm": 999.0,
                "f_score": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "iou": 0.0,
            },
        }

    # 1. Sample surface points
    pts_gt_raw, _ = trimesh.sample.sample_surface(mesh_gt, sample_count)
    pts_gen_raw, _ = trimesh.sample.sample_surface(mesh_gen, sample_count)

    # 2. Raw Mode Metrics
    raw_metrics = compute_chamfer_and_fscore(pts_gt_raw, pts_gen_raw, threshold=raw_threshold_mm)
    raw_iou = compute_volumetric_iou(mesh_gt, mesh_gen)
    raw_metrics["iou"] = raw_iou
    raw_metrics["chamfer_distance_mm"] = raw_metrics.pop("chamfer_distance")

    # 3. Normalised Mode Metrics (Centred at origin + Scaled to unit box)
    mesh_gt_norm, _, _ = normalize_mesh(mesh_gt)
    mesh_gen_norm, _, _ = normalize_mesh(mesh_gen)

    pts_gt_norm, _ = trimesh.sample.sample_surface(mesh_gt_norm, sample_count)
    pts_gen_norm, _ = trimesh.sample.sample_surface(mesh_gen_norm, sample_count)

    norm_metrics = compute_chamfer_and_fscore(pts_gt_norm, pts_gen_norm, threshold=norm_threshold)
    norm_iou = compute_volumetric_iou(mesh_gt_norm, mesh_gen_norm, pitch=0.02)
    norm_metrics["iou"] = norm_iou

    return {
        "valid_meshes": True,
        "normalised": norm_metrics,
        "raw": raw_metrics,
    }
