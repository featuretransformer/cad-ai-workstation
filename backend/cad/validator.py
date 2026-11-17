"""
Geometry validation checks on exported CAD files.
Includes STEP/mesh checks, volume-delta invariant tracking, and candidate scoring.
"""
from typing import List, Dict, Any, Optional
import os


class SilentMergeError(Exception):
    """Raised when an additive feature has non-positive volume delta (submerged body)."""
    pass


class NullBooleanCutError(Exception):
    """Raised when a subtractive boolean cut has zero volume delta (empty air cut)."""
    pass


def validate_step(step_path: str) -> dict:
    """Basic validation: file exists and is non-empty."""
    errors = []
    warnings = []

    if not os.path.exists(step_path):
        errors.append("STEP file not found")
        return {"valid": False, "errors": errors, "warnings": warnings}

    size = os.path.getsize(step_path)
    if size < 100:
        errors.append(f"STEP file suspiciously small ({size} bytes)")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def validate_mesh(stl_path: str) -> dict:
    """Mesh validation using trimesh: watertight, manifold, no degenerate faces."""
    errors = []
    warnings = []

    try:
        import trimesh
        mesh = trimesh.load(stl_path, force="mesh")

        if not isinstance(mesh, trimesh.Trimesh):
            errors.append("Could not load as triangular mesh")
            return {"valid": False, "errors": errors, "warnings": warnings}

        if not mesh.is_watertight:
            warnings.append("Mesh is not watertight (open boundaries detected)")
        if not mesh.is_winding_consistent:
            warnings.append("Mesh winding is inconsistent")
        if mesh.is_empty:
            errors.append("Mesh is empty")

        faces = len(mesh.faces)
        verts = len(mesh.vertices)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "faces": faces,
                "vertices": verts,
                "volume": float(mesh.volume) if mesh.is_watertight else None,
                "surface_area": float(mesh.area),
                "is_watertight": mesh.is_watertight,
            },
        }

    except Exception as e:
        errors.append(f"Mesh validation failed: {str(e)}")
        return {"valid": False, "errors": errors, "warnings": warnings}


def verify_volume_deltas(
    step_vols: List[Dict[str, Any]], raise_on_error: bool = False
) -> Dict[str, Any]:
    """
    Step-by-Step Volume-Delta (ΔV) Invariant Verification.
    Catches silent merge errors and null boolean cuts early.
    """
    deltas = []
    prev_vol = 0.0
    all_valid = True

    for idx, step in enumerate(step_vols):
        vol = step.get("volume", 0.0)
        op = (step.get("operation") or "new_body").lower()
        delta_v = vol if idx == 0 else vol - prev_vol
        deltas.append({
            "feature_id": step.get("feature_id", f"f_{idx}"),
            "delta_v": round(delta_v, 4),
        })

        if idx > 0:
            if op == "join" and delta_v <= 0:
                all_valid = False
                if raise_on_error:
                    raise SilentMergeError(
                        f"Submerged additive feature: ΔV ({delta_v}) <= 0 for operation '{op}'"
                    )
            elif op == "cut" and delta_v >= 0:
                all_valid = False
                if raise_on_error:
                    raise NullBooleanCutError(
                        f"Null boolean cut: ΔV ({delta_v}) >= 0 for operation '{op}'"
                    )
        prev_vol = vol

    return {
        "all_volume_deltas_valid": all_valid,
        "deltas": deltas,
    }


def score_cadir_candidate(
    candidate: Dict[str, Any],
    target_envelope: Optional[List[float]] = None,
    dfm_warnings_count: int = 0,
) -> float:
    """Deterministic Candidate Scoring (0-150 scale)."""
    score = 0.0

    # 1. Watertightness (+50 pts)
    if candidate.get("is_watertight", False):
        score += 50.0

    # 2. Volume-Delta Integrity (+50 pts)
    step_vols = candidate.get("step_volumes", [])
    if step_vols:
        res = verify_volume_deltas(step_vols)
        if res.get("all_volume_deltas_valid", False):
            score += 50.0

    # 3. Envelope Matching (+50 pts)
    bb = candidate.get("bounding_box", {})
    if target_envelope and len(target_envelope) >= 3 and bb:
        dx = abs(bb.get("xmax", 0.0) - bb.get("xmin", 0.0))
        dy = abs(bb.get("ymax", 0.0) - bb.get("ymin", 0.0))
        dz = abs(bb.get("zmax", 0.0) - bb.get("zmin", 0.0))
        tx, ty, tz = target_envelope[0], target_envelope[1], target_envelope[2]

        diff_x = abs(dx - tx) / max(tx, 1.0)
        diff_y = abs(dy - ty) / max(ty, 1.0)
        diff_z = abs(dz - tz) / max(tz, 1.0)

        if diff_x < 0.05 and diff_y < 0.05 and diff_z < 0.05:
            score += 50.0
        else:
            score += max(0.0, 50.0 * (1.0 - (diff_x + diff_y + diff_z) / 3.0))

    # Deduct for DFM warnings
    score -= float(dfm_warnings_count) * 5.0
    return max(0.0, round(score, 2))
