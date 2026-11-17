"""
Scoring for the V2 benchmark.

Two independent evidence streams are combined:

1. **Geometry** - measured from the generated STEP/STL against the record's
   ``expected`` contract (never from prompt text):
     * bounding-box dimensions (per axis, X/Y swap tolerated)
     * solid volume
     * placement (min / max corner in mm, absolute world coordinates)
     * cylindrical hole topology (count + diameters), reconstructed from
       OpenCASCADE cylindrical faces and classified concave/convex by sampling
       the tessellated solid.

2. **Shape** - the candidate is re-rendered with the exact camera and shading
   pipeline used to produce the reference PNG (orthographic iso, azimuth 45,
   elevation 35.264, auto-framed).  Because the renderer normalises scale and
   translation, this isolates *shape* from *size*.  Silhouette IoU and a
   boundary-distance measure are computed against the shipped reference render.

Scoring is level-aware: L2/L3 prompts contain a complete specification and are
graded strictly; L0/L1 prompts intentionally omit the dimensions, so they are
graded on recognition (valid solid + matching shape) and their strict scores are
reported separately as a diagnostic.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = PROJECT_ROOT / "eval"
BACKEND_DIR = PROJECT_ROOT / "backend"
for _p in (str(EVAL_DIR), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ─── Tunable acceptance thresholds ────────────────────────────────────────────
TOL_BBOX_PCT = 2.0          # per-axis dimensional tolerance
TOL_VOLUME_PCT = 5.0        # solid volume tolerance
TOL_PLACEMENT_MM = 1.0      # absolute corner placement tolerance
TOL_HOLE_DIA_PCT = 5.0      # hole diameter tolerance
IOU_SHAPE_PASS = 0.90       # silhouette IoU for a "shape match"
IOU_RECOGNITION_PASS = 0.80  # looser bar used for under-specified L0/L1
CHAMFER_SHAPE_PASS = 3.0    # boundary distance, % of sqrt(area)


# ─── Geometry extraction ─────────────────────────────────────────────────────

def _full_circles(face) -> List[Any]:
    """Full (360 deg) circular edges of a cylindrical face."""
    out = []
    for e in face.edges():
        try:
            if e.geom_type.name != "CIRCLE":
                continue
            r = float(e.radius)
            if r <= 1e-9:
                continue
            if abs(float(e.length) - 2.0 * math.pi * r) < 0.02 * r:
                out.append(e)
        except Exception:
            continue
    return out


def _axis_from_circles(circles: List[Any]) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Returns (point_on_axis, unit_direction) for a set of coaxial circle edges."""
    if not circles:
        return None
    centres = np.array(
        [[float(e.arc_center.X), float(e.arc_center.Y), float(e.arc_center.Z)] for e in circles]
    )
    if len(centres) >= 2:
        diffs = centres - centres[0]
        norms = np.linalg.norm(diffs, axis=1)
        i = int(np.argmax(norms))
        if norms[i] > 1e-6:
            direction = diffs[i] / norms[i]
            return centres[0], direction
    # Single circle: fall back to the world Z axis convention
    return centres[0], np.array([0.0, 0.0, 1.0])


def _sample_radial(axis_pt: np.ndarray, axis_dir: np.ndarray, factor: float, radius: float) -> np.ndarray:
    """Point at ``factor * radius`` from the axis in a direction perpendicular to it."""
    helper = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(helper, axis_dir))) > 0.9:
        helper = np.array([0.0, 1.0, 0.0])
    radial = np.cross(axis_dir, helper)
    radial /= np.linalg.norm(radial)
    return axis_pt + radial * (factor * radius)


def _inside(shape, point: np.ndarray) -> bool:
    """Point-in-solid test using the OpenCASCADE solid classifier."""
    try:
        from build123d import Vector

        return bool(shape.is_inside(Vector(float(point[0]), float(point[1]), float(point[2]))))
    except Exception:
        return False


def _line_distance(p1: np.ndarray, d1: np.ndarray, p2: np.ndarray, d2: np.ndarray) -> float:
    """Shortest distance between two infinite lines."""
    n = np.cross(d1, d2)
    nn = float(np.linalg.norm(n))
    if nn < 1e-6:  # parallel
        return float(np.linalg.norm(np.cross(p2 - p1, d1)))
    return abs(float(np.dot(p2 - p1, n / nn)))


def _merge_intersecting_bores(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges same-diameter bores whose axes meet (one bent channel, many faces)."""
    merged = True
    while merged and len(groups) > 1:
        merged = False
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                a, b = groups[i], groups[j]
                dia_a, dia_b = min(a["dia"]), min(b["dia"])
                if abs(dia_a - dia_b) / max(dia_a, dia_b, 1e-6) > 0.03:
                    continue
                if _line_distance(a["point"], a["dir"], b["point"], b["dir"]) > 0.5 * min(dia_a, dia_b):
                    continue
                a["dia"].extend(b["dia"])
                groups.pop(j)
                merged = True
                break
            if merged:
                break
    return groups


def extract_holes(step_path: Optional[str], stl_path: Optional[str]) -> Dict[str, Any]:
    """
    Recovers cylindrical hole features from the B-Rep and classifies each as a
    bore (concave) or a boss (convex) by point-containment sampling.

    Groups coaxial bores (e.g. a counterbore + its clearance hole) into one
    logical hole whose diameter is the smallest (through) diameter.
    """
    empty = {"hole_count": 0, "hole_diameters": [], "hole_axes": [], "cyl_faces": 0}
    if not step_path or not Path(step_path).exists():
        return empty
    try:
        from build123d import import_step
    except Exception:
        return empty

    try:
        shape = import_step(str(step_path))
    except Exception:
        return empty

    cylinders = []
    try:
        for face in shape.faces():
            if face.geom_type.name != "CYLINDER":
                continue
            circles = _full_circles(face)
            if len(circles) < 1:
                continue
            axis = _axis_from_circles(circles)
            if axis is None:
                continue
            pt, direction = axis
            r = float(np.mean([float(e.radius) for e in circles]))
            cylinders.append({"radius": r, "point": pt, "dir": direction})
    except Exception:
        return empty

    # Concavity test: material just inside the radius => external boss, else bore.
    bores = []
    for cyl in cylinders:
        inner = _sample_radial(cyl["point"], cyl["dir"], 0.9, cyl["radius"])
        outer = _sample_radial(cyl["point"], cyl["dir"], 1.1, cyl["radius"])
        inside_inner = _inside(shape, inner)
        inside_outer = _inside(shape, outer)
        is_bore = bool(inside_outer and not inside_inner)
        if is_bore:
            bores.append(cyl)

    # Group coaxial bores into logical holes.
    groups: List[Dict[str, Any]] = []
    for cyl in bores:
        placed = False
        for g in groups:
            d = float(np.dot(cyl["dir"], g["dir"]))
            if abs(abs(d) - 1.0) > 0.02:
                continue
            v = cyl["point"] - g["point"]
            perp = v - np.dot(v, g["dir"]) * g["dir"]
            if float(np.linalg.norm(perp)) <= 0.75:
                g["dia"].append(cyl["radius"] * 2.0)
                placed = True
                break
        if not placed:
            groups.append({"point": cyl["point"], "dir": cyl["dir"], "dia": [cyl["radius"] * 2.0]})

    # Merge bent channels: two same-diameter bores whose axes meet are one
    # continuous bore (e.g. the two straight legs of a pipe elbow joined by a
    # toroidal bend).  Parallel holes (bolt patterns) are never merged.
    groups = _merge_intersecting_bores(groups)

    diameters = sorted(round(min(g["dia"]), 3) for g in groups)
    axes = [
        {
            "point": [round(float(v), 3) for v in g["point"]],
            "dir": [round(float(v), 3) for v in g["dir"]],
        }
        for g in groups
    ]
    return {
        "hole_count": len(groups),
        "hole_diameters": diameters,
        "hole_axes": axes,
        "cyl_faces": len(cylinders),
    }


def extract_geometry(step_path: Optional[str], stl_path: Optional[str]) -> Dict[str, Any]:
    """Measures the generated solid: validity, bbox, volume and hole topology."""
    res: Dict[str, Any] = {
        "valid": False,
        "watertight": False,
        "volume": 0.0,
        "bbox_min": [0.0, 0.0, 0.0],
        "bbox_max": [0.0, 0.0, 0.0],
        "bbox_dims": [0.0, 0.0, 0.0],
        "hole_count": 0,
        "hole_diameters": [],
        "hole_axes": [],
    }

    if stl_path and Path(stl_path).exists() and Path(stl_path).stat().st_size > 50:
        try:
            import trimesh

            mesh = trimesh.load(str(stl_path), force="mesh")
            if isinstance(mesh, trimesh.Trimesh) and not mesh.is_empty:
                res["watertight"] = bool(mesh.is_watertight)
                bounds = mesh.bounds
                res["bbox_min"] = [float(v) for v in bounds[0]]
                res["bbox_max"] = [float(v) for v in bounds[1]]
                res["bbox_dims"] = [float(bounds[1][i] - bounds[0][i]) for i in range(3)]
                if mesh.is_watertight:
                    res["volume"] = float(abs(mesh.volume))
                res["valid"] = True
        except Exception:
            pass

    if step_path and Path(step_path).exists() and Path(step_path).stat().st_size > 50:
        try:
            from build123d import import_step

            shape = import_step(str(step_path))
            if shape is not None and getattr(shape, "is_valid", False):
                if float(shape.volume) > 0:
                    res["volume"] = float(shape.volume)
                    res["valid"] = True
                bb = shape.bounding_box()
                res["bbox_min"] = [float(bb.min.X), float(bb.min.Y), float(bb.min.Z)]
                res["bbox_max"] = [float(bb.max.X), float(bb.max.Y), float(bb.max.Z)]
                res["bbox_dims"] = [
                    float(bb.max.X - bb.min.X),
                    float(bb.max.Y - bb.min.Y),
                    float(bb.max.Z - bb.min.Z),
                ]
        except Exception:
            pass

    res.update(extract_holes(step_path, stl_path))
    res["valid"] = bool(res["valid"] and res["volume"] > 0.0)
    return res


# ─── Rendering & shape comparison ────────────────────────────────────────────

def _sharp_edges(mesh) -> List[Any]:
    """
    Feature edges only (dihedral angle > 25 deg).

    The golden reference renders draw sharp feature edges, not every triangle
    edge, so using the same rule is required for a comparable image.
    """
    edges = []
    try:
        face_angles = mesh.face_adjacency_angles
        sharp_mask = face_angles > np.radians(25)
        for a, b in mesh.face_adjacency_edges[sharp_mask]:
            edges.append((mesh.vertices[a], mesh.vertices[b]))
    except Exception:
        pass
    return edges


def render_candidate(stl_path: str) -> Optional[Image.Image]:
    """Re-renders a candidate STL with the reference camera/shading pipeline."""
    try:
        import trimesh
        from build_golden_set import render_mesh_to_isometric

        mesh = trimesh.load(str(stl_path), force="mesh")
        if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
            return None
        mesh.merge_vertices()
        edges = _sharp_edges(mesh)
        return render_mesh_to_isometric(mesh.vertices, mesh.faces, edges)
    except Exception:
        return None


def silhouette(img: Image.Image) -> np.ndarray:
    """Boolean mask of non-background pixels (the render background is white)."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    return a.sum(axis=2) < 740


def _boundary(mask: np.ndarray) -> np.ndarray:
    pad = np.pad(mask, 1, mode="constant", constant_values=False)
    eroded = (
        pad[1:-1, 1:-1]
        & pad[:-2, 1:-1]
        & pad[2:, 1:-1]
        & pad[1:-1, :-2]
        & pad[1:-1, 2:]
    )
    return mask & ~eroded


def compare_shape(ref_img: Image.Image, gen_img: Image.Image) -> Dict[str, float]:
    """Scale/translation-invariant shape comparison of two iso renders."""
    from scipy.ndimage import distance_transform_edt

    a, b = silhouette(ref_img), silhouette(gen_img)
    inter = float(np.logical_and(a, b).sum())
    union = float(np.logical_or(a, b).sum())
    iou = inter / union if union > 0 else 0.0

    ba, bb = _boundary(a), _boundary(b)
    if ba.sum() == 0 or bb.sum() == 0:
        return {"iou": round(iou, 4), "chamfer_pct": 100.0}

    da = distance_transform_edt(~ba)
    db = distance_transform_edt(~bb)
    # symmetric mean distance between boundaries, normalised by object size
    d = 0.5 * (float(da[bb].mean()) + float(db[ba].mean()))
    norm = math.sqrt(max(inter, 1.0))
    return {"iou": round(iou, 4), "chamfer_pct": round(100.0 * d / norm, 3)}


# ─── Dimensional / placement scoring ────────────────────────────────────────

def _axis_errors(gen: List[float], exp: List[float], swap_xy: bool) -> List[float]:
    if swap_xy:
        gen = [gen[1], gen[0], gen[2]]
    return [abs(g - e) / e * 100.0 if e else 0.0 for g, e in zip(gen, exp)]


def score_dimensions(gen: List[float], exp: List[float]) -> Dict[str, Any]:
    """
    Axis-wise dimensional error.

    Orientation is graded strictly: a part whose 80 mm length runs along the
    wrong axis is a different part, even though its sorted dimensions match.
    The X/Y-swapped error is still reported as a diagnostic.
    """
    direct = _axis_errors(gen, exp, swap_xy=False)
    swapped = _axis_errors(gen, exp, swap_xy=True)
    use_swap = sum(swapped) < sum(direct)
    return {
        "errors_pct": [round(e, 3) for e in direct],
        "max_error_pct": round(max(direct), 3),
        "mean_error_pct": round(float(np.mean(direct)), 3),
        "pass": bool(max(direct) <= TOL_BBOX_PCT),
        "xy_swapped_diag": bool(use_swap),
        "pass_if_xy_swapped": bool(max(swapped) <= TOL_BBOX_PCT),
    }


def score_placement(
    gen_min: List[float], gen_max: List[float], exp_min: List[float], exp_max: List[float], swap_xy: bool
) -> Dict[str, Any]:
    if swap_xy:
        gen_min = [gen_min[1], gen_min[0], gen_min[2]]
        gen_max = [gen_max[1], gen_max[0], gen_max[2]]
    dmin = [g - e for g, e in zip(gen_min, exp_min)]
    dmax = [g - e for g, e in zip(gen_max, exp_max)]
    corner_err = max(
        float(np.linalg.norm(dmin)), float(np.linalg.norm(dmax))
    )
    return {
        "min_delta_mm": [round(v, 3) for v in dmin],
        "max_delta_mm": [round(v, 3) for v in dmax],
        "corner_error_mm": round(corner_err, 3),
        "centroid_error_mm": round(float(np.linalg.norm([(a + b) / 2 for a, b in zip(dmin, dmax)])), 3),
        "pass": bool(corner_err <= TOL_PLACEMENT_MM),
    }


def score_holes(gen_dias: List[float], exp_dias: List[float], gen_count: int, exp_count: int) -> Dict[str, Any]:
    """Count match plus greedy diameter matching (nearest, within tolerance)."""
    matched = 0
    used = set()
    for e in sorted(exp_dias):
        best_i, best_err = None, None
        for i, g in enumerate(gen_dias):
            if i in used:
                continue
            err = abs(g - e) / e * 100.0 if e else 100.0
            if best_err is None or err < best_err:
                best_i, best_err = i, err
        if best_i is not None and best_err is not None and best_err <= TOL_HOLE_DIA_PCT:
            used.add(best_i)
            matched += 1
    dia_ok = (len(exp_dias) == 0) or (matched == len(exp_dias))
    count_ok = gen_count == exp_count
    return {
        "expected_count": exp_count,
        "generated_count": gen_count,
        "count_match": bool(count_ok),
        "expected_diameters": [round(float(d), 3) for d in exp_dias],
        "generated_diameters": [round(float(d), 3) for d in gen_dias],
        "diameters_matched": matched,
        "diameters_expected": len(exp_dias),
        "pass": bool(count_ok and dia_ok),
    }


# ─── Case-level scoring ─────────────────────────────────────────────────────

def score_case(
    case,
    level: str,
    generation: Dict[str, Any],
    reference_img: Optional[Image.Image],
) -> Dict[str, Any]:
    """
    Builds the full, flat record for one (part, prompt-level) evaluation case.
    ``generation`` must contain: success, step_path, stl_path, latency_sec, ...
    """
    step_path = generation.get("step_path")
    stl_path = generation.get("stl_path")
    geo = extract_geometry(step_path, stl_path)

    dims = score_dimensions(geo["bbox_dims"], case.bbox)
    placement = score_placement(
        geo["bbox_min"], geo["bbox_max"], case.placement_min, case.placement_max, swap_xy=False
    )
    holes = score_holes(geo["hole_diameters"], case.hole_diameters, geo["hole_count"], case.hole_count)
    vol_err = (
        abs(geo["volume"] - case.volume) / case.volume * 100.0 if case.volume > 0 and geo["volume"] > 0 else 100.0
    )
    volume = {
        "generated_mm3": round(geo["volume"], 2),
        "expected_mm3": round(case.volume, 2),
        "error_pct": round(vol_err, 3),
        "pass": bool(vol_err <= TOL_VOLUME_PCT),
    }

    # Shape evidence (only meaningful when the reference render exists)
    shape: Dict[str, Any] = {"iou": 0.0, "chamfer_pct": 100.0, "render_ok": False}
    gen_img = None
    if geo["valid"] and stl_path:
        gen_img = render_candidate(stl_path)
    if gen_img is not None and reference_img is not None:
        shape.update(compare_shape(reference_img, gen_img))
        shape["render_ok"] = True

    valid = bool(geo["valid"] and generation.get("success", False))
    strict_pass = bool(valid and dims["pass"] and placement["pass"] and holes["pass"] and volume["pass"])
    shape_pass = bool(shape["render_ok"] and shape["iou"] >= IOU_SHAPE_PASS)
    recognition_pass = bool(valid and shape["render_ok"] and shape["iou"] >= IOU_RECOGNITION_PASS)

    if level in ("L2", "L3"):
        overall_pass = bool(strict_pass and shape_pass)
        basis = "strict"
    else:
        overall_pass = bool(recognition_pass)
        basis = "recognition"

    # Composite aspect scores in [0,1] - useful for tracking gradual progress
    def _clip(x):
        return float(min(1.0, max(0.0, x)))

    aspects = {
        "validity": 1.0 if valid else 0.0,
        "dimensions": _clip(1.0 - dims["max_error_pct"] / 10.0),
        "volume": _clip(1.0 - volume["error_pct"] / 20.0),
        "positioning": _clip(1.0 - placement["corner_error_mm"] / 5.0),
        "topology": 1.0 if holes["pass"] else 0.0,
        "shape": _shape_score(shape["iou"], shape["chamfer_pct"]),
    }

    return {
        "id": case.id,
        "family": case.family,
        "tier": case.tier,
        "level": level,
        "prompt": case.prompt(level),
        "valid_solid": valid,
        "watertight": bool(geo["watertight"]),
        "strict_pass": strict_pass,
        "recognition_pass": recognition_pass,
        "overall_pass": overall_pass,
        "pass_basis": basis,
        "dim": dims,
        "volume": volume,
        "placement": placement,
        "holes": holes,
        "shape": shape,
        "aspects": aspects,
        "geometry": {
            "bbox_dims": [round(v, 3) for v in geo["bbox_dims"]],
            "bbox_min": [round(v, 3) for v in geo["bbox_min"]],
            "bbox_max": [round(v, 3) for v in geo["bbox_max"]],
        },
        "expected": {
            "bbox_mm": case.bbox,
            "volume_mm3": round(case.volume, 3),
            "placement_min": case.placement_min,
            "placement_max": case.placement_max,
            "holes": case.hole_count,
        },
        "generation": {
            "success": bool(generation.get("success", False)),
            "latency_sec": generation.get("latency_sec"),
            "error": generation.get("error", ""),
            "cadir_features": generation.get("cadir_features"),
            "cadir_name": generation.get("cadir_name"),
            "component_family": generation.get("component_family"),
            "cad_lines": generation.get("cad_lines"),
            "design_id": generation.get("design_id"),
            "step_path": step_path,
            "stl_path": stl_path,
        },
    }


def _shape_score(iou: float, chamfer_pct: float) -> float:
    """Blends silhouette overlap with boundary-distance agreement into [0, 1]."""
    return float(min(1.0, max(0.0, 0.5 * iou + 0.5 * math.exp(-chamfer_pct / 10.0))))


def rescore_stored(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recomputes the pass flags of an already-collected record from its stored
    measurements.  Used when the acceptance thresholds change (e.g. switching
    from orientation-tolerant to strict orientation grading) so historical runs
    can be compared like-for-like without re-running the models.
    """
    geo = record.get("geometry") or {}
    exp = record.get("expected") or {}
    dims = score_dimensions(list(geo.get("bbox_dims") or [0, 0, 0]), list(exp.get("bbox_mm") or [1, 1, 1]))
    placement = score_placement(
        list(geo.get("bbox_min") or [0, 0, 0]),
        list(geo.get("bbox_max") or [0, 0, 0]),
        list(exp.get("placement_min") or [0, 0, 0]),
        list(exp.get("placement_max") or [0, 0, 0]),
        swap_xy=False,
    )
    holes = record.get("holes") or {}
    valid = bool(record.get("valid_solid"))
    volume = record.get("volume") or {}
    shape = record.get("shape") or {"iou": 0.0}

    strict = bool(
        valid
        and dims["pass"]
        and placement["pass"]
        and holes.get("pass")
        and volume.get("pass")
    )
    shape_pass = bool(shape.get("iou", 0.0) >= IOU_SHAPE_PASS)
    recognition = bool(valid and shape.get("iou", 0.0) >= IOU_RECOGNITION_PASS)
    level = record.get("level", "L2")
    if level in ("L2", "L3"):
        overall = bool(strict and shape_pass)
        basis = "strict"
    else:
        overall = recognition
        basis = "recognition"

    record["dim"] = dims
    record["placement"] = placement
    record["strict_pass"] = strict
    record["shape_pass"] = shape_pass
    record["recognition_pass"] = recognition
    record["overall_pass"] = overall
    record["pass_basis"] = basis
    record.setdefault("aspects", {})
    record["aspects"].update({
        "dimensions": float(min(1.0, max(0.0, 1.0 - dims["max_error_pct"] / 10.0))),
        "positioning": float(min(1.0, max(0.0, 1.0 - placement["corner_error_mm"] / 5.0))),
        "shape": _shape_score(shape.get("iou", 0.0), shape.get("chamfer_pct", 100.0)),
    })
    return record
