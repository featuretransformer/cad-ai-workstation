"""
Geometry Feature Extractor for CAD Evaluation.
Extracts rigorous ground-truth and candidate metrics from STEP (OpenCASCADE B-Rep)
and STL (trimesh surface) representations.
Never parses prompt strings — all dimensional properties are derived from geometry.
"""
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

try:
    import trimesh
except ImportError:
    trimesh = None


def extract_cad_features(step_path: Optional[str] = None, stl_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts physical geometric features from a CAD STEP solid and/or STL mesh.
    Returns:
        - valid: bool (has valid geometry)
        - is_closed_solid: bool
        - is_watertight: bool
        - volume: float (mm3)
        - surface_area: float (mm2)
        - bbox_min: [x, y, z]
        - bbox_max: [x, y, z]
        - bbox_dims: [dx, dy, dz]
        - centroid: [x, y, z]
        - hole_count: int
        - holes: List[Dict] with diameter, radius, depth, center, axis
    """
    res: Dict[str, Any] = {
        "valid": False,
        "is_closed_solid": False,
        "is_watertight": False,
        "volume": 0.0,
        "surface_area": 0.0,
        "bbox_min": [0.0, 0.0, 0.0],
        "bbox_max": [0.0, 0.0, 0.0],
        "bbox_dims": [0.0, 0.0, 0.0],
        "centroid": [0.0, 0.0, 0.0],
        "hole_count": 0,
        "holes": [],
        "faces_count": 0,
        "edges_count": 0,
    }

    mesh = None
    if stl_path and Path(stl_path).exists():
        try:
            mesh = trimesh.load(str(stl_path), force="mesh")
        except Exception:
            mesh = None

    # Step 1: OpenCASCADE B-Rep Inspection (if STEP exists)
    if step_path and Path(step_path).exists() and Path(step_path).stat().st_size > 50:
        try:
            from build123d import import_step
            shape = import_step(str(step_path))
            if shape and hasattr(shape, "is_valid") and shape.is_valid:
                res["valid"] = True
                res["is_closed_solid"] = getattr(shape, "is_closed", True)
                res["volume"] = float(shape.volume)

                bb = shape.bounding_box()
                res["bbox_min"] = [float(bb.min.X), float(bb.min.Y), float(bb.min.Z)]
                res["bbox_max"] = [float(bb.max.X), float(bb.max.Y), float(bb.max.Z)]
                res["bbox_dims"] = [
                    float(bb.max.X - bb.min.X),
                    float(bb.max.Y - bb.min.Y),
                    float(bb.max.Z - bb.min.Z),
                ]
                res["centroid"] = [
                    float((bb.max.X + bb.min.X) / 2.0),
                    float((bb.max.Y + bb.min.Y) / 2.0),
                    float((bb.max.Z + bb.min.Z) / 2.0),
                ]

                faces = list(shape.faces())
                edges = list(shape.edges())
                res["faces_count"] = len(faces)
                res["edges_count"] = len(edges)

                # Identify cylindrical holes
                cyl_faces = [f for f in faces if f.geom_type.name == "CYLINDER"]
                holes = []
                seen = []

                for f in cyl_faces:
                    try:
                        r = float(f.radius)
                        c = f.center()
                        cx, cy, cz = round(float(c.X), 2), round(float(c.Y), 2), round(float(c.Z), 2)
                        diam = round(r * 2.0, 3)

                        # Deduplicate split cylinder seams
                        is_dup = any(
                            math.isclose(cx, sx, abs_tol=0.25)
                            and math.isclose(cy, sy, abs_tol=0.25)
                            and math.isclose(diam, sd, abs_tol=0.25)
                            for sx, sy, sd in seen
                        )
                        if not is_dup:
                            seen.append((cx, cy, diam))
                            holes.append({
                                "diameter_mm": diam,
                                "radius_mm": round(r, 3),
                                "center": [cx, cy, cz],
                            })
                    except Exception:
                        continue

                res["holes"] = holes
                res["hole_count"] = len(holes)
        except Exception:
            pass

    # Step 2: Mesh Fallback and Watertightness Verification
    if mesh is not None and isinstance(mesh, trimesh.Trimesh) and not mesh.is_empty:
        res["valid"] = True
        res["is_watertight"] = bool(mesh.is_watertight)
        res["surface_area"] = float(mesh.area)

        if not res["is_closed_solid"]:
            res["is_closed_solid"] = bool(mesh.is_watertight)

        if res["volume"] <= 0.0 and mesh.is_watertight:
            res["volume"] = float(mesh.volume)

        if sum(res["bbox_dims"]) <= 0.0:
            bounds = mesh.bounds
            res["bbox_min"] = [float(bounds[0][0]), float(bounds[0][1]), float(bounds[0][2])]
            res["bbox_max"] = [float(bounds[1][0]), float(bounds[1][1]), float(bounds[1][2])]
            res["bbox_dims"] = [
                float(bounds[1][0] - bounds[0][0]),
                float(bounds[1][1] - bounds[0][1]),
                float(bounds[1][2] - bounds[0][2]),
            ]
            res["centroid"] = [float(mesh.centroid[0]), float(mesh.centroid[1]), float(mesh.centroid[2])]

    return res
