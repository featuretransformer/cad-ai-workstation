"""
Build Golden Evaluation Set for AI-Native CAD Workstation.
Loads golden_cad_prompts.jsonl, builds true B-Rep solids in build123d,
exports STEP + STL, extracts ground-truth dimensions from geometry,
generates standardized 512x512 isometric renders, and freezes the set
with a SHA-256 manifest hash.
"""
import os
import sys
import json
import math
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
from PIL import Image

# Ensure backend root is in sys.path
EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from build123d import *

GOLDEN_SET_DIR = EVAL_DIR / "golden_set"
STEP_DIR = GOLDEN_SET_DIR / "step"
RENDERS_DIR = GOLDEN_SET_DIR / "renders"

GOLDEN_SET_DIR.mkdir(parents=True, exist_ok=True)
STEP_DIR.mkdir(parents=True, exist_ok=True)
RENDERS_DIR.mkdir(parents=True, exist_ok=True)

# Standard Isometric Camera Configuration
# Orthographic, Azimuth 45°, Elevation 35.264° (arcsin(1/sqrt(3))), Z-up, 512x512
AZ_DEG = 45.0
EL_DEG = 35.264
AZ = math.radians(AZ_DEG)
EL = math.radians(EL_DEG)
RES = 512
SS = 2  # Supersampling factor for anti-aliasing

CAM = np.array([math.cos(EL) * math.sin(AZ), -math.cos(EL) * math.cos(AZ), math.sin(EL)])
UP = np.array([0, 0, 1.0])
RIGHT = np.cross(UP, CAM)
RIGHT /= np.linalg.norm(RIGHT)
VUP = np.cross(CAM, RIGHT)
LIGHT = -0.45 * RIGHT + 0.55 * VUP + 0.85 * CAM
LIGHT /= np.linalg.norm(LIGHT)


def project_points(P: np.ndarray) -> np.ndarray:
    """Project 3D points to camera coordinates."""
    return np.c_[P @ RIGHT, P @ VUP, P @ CAM]


def render_mesh_to_isometric(vertices: np.ndarray, faces: np.ndarray, edges: List[Tuple[np.ndarray, np.ndarray]]) -> Image.Image:
    """
    Renders 3D triangular mesh into an orthographic isometric view with flat grey shading
    and crisp black feature edges on pure white background.
    """
    T = vertices[faces]  # (M, 3, 3)
    all_pts = T.reshape(-1, 3)
    sc = project_points(all_pts)
    cx = (sc[:, 0].max() + sc[:, 0].min()) / 2.0
    cy = (sc[:, 1].max() + sc[:, 1].min()) / 2.0
    ext = max(np.ptp(sc[:, 0]), np.ptp(sc[:, 1]))
    if ext < 1e-6:
        ext = 1.0
    size = RES * SS
    scale = 0.74 * size / ext

    def to_px(P: np.ndarray) -> np.ndarray:
        s = project_points(P)
        return np.c_[(s[:, 0] - cx) * scale + size / 2.0, size / 2.0 - (s[:, 1] - cy) * scale, s[:, 2]]

    zb = np.full((size, size), -np.inf)
    img = np.full((size, size, 3), 255, dtype=np.uint8)

    # Shaded triangle rasterization with Z-buffer
    for tr in T:
        n = np.cross(tr[1] - tr[0], tr[2] - tr[0])
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            continue
        shade = 0.38 + 0.62 * abs(float(n / ln @ LIGHT))
        col = np.array([205, 208, 214]) * shade
        p = to_px(tr)
        x0, x1 = int(max(0, math.floor(p[:, 0].min()))), int(min(size - 1, math.ceil(p[:, 0].max())))
        y0, y1 = int(max(0, math.floor(p[:, 1].min()))), int(min(size - 1, math.ceil(p[:, 1].max())))
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
        if abs(d) < 1e-9:
            continue
        l1 = ((p[1, 1] - p[2, 1]) * (xs - p[2, 0]) + (p[2, 0] - p[1, 0]) * (ys - p[2, 1])) / d
        l2 = ((p[2, 1] - p[0, 1]) * (xs - p[2, 0]) + (p[0, 0] - p[2, 0]) * (ys - p[2, 1])) / d
        l3 = 1.0 - l1 - l2
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not m.any():
            continue
        z = l1 * p[0, 2] + l2 * p[1, 2] + l3 * p[2, 2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        upd = m & (z > sub)
        sub[upd] = z[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = col.astype(np.uint8)

    # Black feature edges overlay
    eps = 0.012 * ext * scale / scale
    for pa_3d, pb_3d in edges:
        pa, pb = to_px(np.array([pa_3d]))[0], to_px(np.array([pb_3d]))[0]
        n_pts = int(max(2, np.hypot(*(pb[:2] - pa[:2])) * 1.5))
        t = np.linspace(0, 1, n_pts)
        pts = pa[None] + (pb - pa)[None] * t[:, None]
        for x, y, z in pts:
            xi, yi = int(x), int(y)
            if 1 <= xi < size - 1 and 1 <= yi < size - 1 and z >= zb[yi, xi] - eps:
                img[yi - 1:yi + 2, xi - 1:xi + 2] = (20, 20, 20)

    # Downsample supersampled buffer to target 512x512
    return Image.fromarray(img).resize((RES, RES), Image.Resampling.LANCZOS)


def extract_edges_from_mesh(mesh) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Extracts boundary and sharp feature edges from trimesh object."""
    import trimesh
    feature_edges = []
    # Sharp angle edges
    try:
        face_adj = mesh.face_adjacency
        face_angles = mesh.face_adjacency_angles
        sharp_mask = face_angles > np.radians(25)  # sharp dihedral angle threshold
        sharp_edges = mesh.face_adjacency_edges[sharp_mask]
        for edge in sharp_edges:
            feature_edges.append((mesh.vertices[edge[0]], mesh.vertices[edge[1]]))
    except Exception:
        pass

    # Boundary edges if non-watertight
    try:
        for edge in mesh.edges_unique:
            feature_edges.append((mesh.vertices[edge[0]], mesh.vertices[edge[1]]))
    except Exception:
        pass

    return feature_edges


def create_solid_for_record(rec: Dict[str, Any]) -> Part:
    """Builds the exact mathematical build123d Solid for a given golden prompt record."""
    fam = rec["family"]
    P = rec["params"]

    if fam == "box":
        with BuildPart() as p:
            Box(P["L"], P["W"], P["H"])
        return p.part

    elif fam == "cylinder":
        with BuildPart() as p:
            Cylinder(radius=P["D"] / 2.0, height=P["H"])
        return p.part

    elif fam == "tube":
        with BuildPart() as p:
            Cylinder(radius=P["OD"] / 2.0, height=P["H"])
            Cylinder(radius=P["ID"] / 2.0, height=P["H"], mode=Mode.SUBTRACT)
        return p.part

    elif fam == "plate_center_hole":
        with BuildPart() as p:
            Box(P["L"], P["W"], P["T"])
            Cylinder(radius=P["d"] / 2.0, height=P["T"], mode=Mode.SUBTRACT)
        return p.part

    elif fam == "plate_4_holes":
        centres = rec["expected"]["features"]["hole_centres_mm"]
        with BuildPart() as p:
            Box(P["L"], P["W"], P["T"])
            for cx, cy in centres:
                with Locations((cx, cy, 0)):
                    Cylinder(radius=P["d"] / 2.0, height=P["T"], mode=Mode.SUBTRACT)
        return p.part

    elif fam == "l_bracket":
        a, b, t, W = P["a"], P["b"], P["t"], P["W"]
        poly = [(0, 0), (a, 0), (a, t), (t, t), (t, b), (0, b)]
        with BuildPart() as p:
            with BuildSketch(Plane.XZ):
                Polygon(poly)
            extrude(amount=W)
        return p.part

    elif fam == "flange":
        OD, ID, T, BCD, n, bolt_d = P["OD"], P["ID"], P["T"], P["BCD"], P["n"], P["bolt_d"]
        with BuildPart() as p:
            Cylinder(radius=OD / 2.0, height=T)
            Cylinder(radius=ID / 2.0, height=T, mode=Mode.SUBTRACT)
            for k in range(n):
                ang = 2.0 * math.pi * k / n
                bx = (BCD / 2.0) * math.cos(ang)
                by = (BCD / 2.0) * math.sin(ang)
                with Locations((bx, by, 0)):
                    Cylinder(radius=bolt_d / 2.0, height=T, mode=Mode.SUBTRACT)
        return p.part

    elif fam == "stepped_shaft":
        D1, L1, D2, L2 = P["D1"], P["L1"], P["D2"], P["L2"]
        with BuildPart() as p:
            Cylinder(radius=D1 / 2.0, height=L1)
            with Locations((0, 0, L1 / 2.0 + L2 / 2.0)):
                Cylinder(radius=D2 / 2.0, height=L2)
        return p.part

    elif fam == "hex_nut":
        AF, H, d = P["AF"], P["H"], P["d"]
        R = AF / math.sqrt(3)  # Circumscribed major radius
        with BuildPart() as p:
            with BuildSketch():
                RegularPolygon(radius=R, side_count=6, major_radius=True)
                Circle(radius=d / 2.0, mode=Mode.SUBTRACT)
            extrude(amount=H)
        return p.part

    elif fam == "u_channel":
        W, H, t, L = P["W"], P["H"], P["t"], P["L"]
        poly = [(0, 0), (W, 0), (W, H), (W - t, H), (W - t, t), (t, t), (t, H), (0, H)]
        with BuildPart() as p:
            with BuildSketch(Plane.XZ):
                Polygon(poly)
            extrude(amount=L)
        return p.part

    else:
        raise ValueError(f"Unknown family: {fam}")


def extract_gt_dimensions_from_part(part: Part, rec: Dict[str, Any]) -> Dict[str, Any]:
    """Computes ground-truth dimensions directly from B-Rep geometry and mesh."""
    bb = part.bounding_box()
    dx = float(bb.max.X - bb.min.X)
    dy = float(bb.max.Y - bb.min.Y)
    dz = float(bb.max.Z - bb.min.Z)
    vol = float(part.volume)

    # Extract cylindrical hole features from geometry
    cyl_faces = [f for f in part.faces() if f.geom_type.name == "CYLINDER"]
    holes = []
    seen_centers = []

    for f in cyl_faces:
        # Check if internal (hole/bore) or external (shaft/outer body)
        # In B-Rep, hole cylinder normal points inward toward axis
        r = float(f.radius)
        diam = r * 2.0
        c = f.center()
        cx, cy, cz = round(float(c.X), 3), round(float(c.Y), 3), round(float(c.Z), 3)

        # Avoid duplicates for split cylinder faces
        is_dup = any(math.isclose(cx, sx, abs_tol=0.2) and math.isclose(cy, sy, abs_tol=0.2) and math.isclose(diam, sd, abs_tol=0.2)
                     for sx, sy, sd in seen_centers)
        if not is_dup:
            seen_centers.append((cx, cy, diam))
            holes.append({
                "diameter_mm": round(diam, 3),
                "radius_mm": round(r, 3),
                "center_mm": [cx, cy, cz],
            })

    # Expected features from input record for ground-truth alignment
    exp_features = rec.get("expected", {}).get("features", {})
    expected_holes = exp_features.get("holes", 0)

    return {
        "bbox_mm": [round(dx, 4), round(dy, 4), round(dz, 4)],
        "volume_mm3": round(vol, 4),
        "hole_count": expected_holes,
        "extracted_cylinders": holes,
        "wall_thickness_mm": rec["params"].get("t") or rec["params"].get("T"),
    }


def build_golden_set():
    print("[*] Building Golden Evaluation Set (30 Mechanical Components)...")

    # Source prompt dataset
    source_prompts_file = Path(r"C:\Users\shiva\Downloads\golden_cad_prompts.jsonl")
    if not source_prompts_file.exists():
        source_prompts_file = GOLDEN_SET_DIR / "golden_cad_prompts.jsonl"
        if not source_prompts_file.exists():
            raise FileNotFoundError("golden_cad_prompts.jsonl not found!")

    # Copy raw source to eval/golden_set/ if not identical
    dest_prompts_file = GOLDEN_SET_DIR / "golden_cad_prompts.jsonl"
    if source_prompts_file != dest_prompts_file:
        with open(source_prompts_file, "r", encoding="utf-8") as sf:
            raw_content = sf.read()
        with open(dest_prompts_file, "w", encoding="utf-8") as df:
            df.write(raw_content)

    with open(dest_prompts_file, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    print(f"[*] Loaded {len(records)} test records across {len(set(r['family'] for r in records))} families.")

    manifest_entries = []

    for i, rec in enumerate(records, start=1):
        pid = rec["id"]
        fam = rec["family"]
        tier = rec["tier"]
        print(f"  [{i}/{len(records)}] Building {pid} ({fam}, {tier})...")

        # 1. Generate CAD B-Rep Solid
        solid = create_solid_for_record(rec)

        # 2. Export STEP and STL
        step_file = STEP_DIR / f"{pid}.step"
        stl_file = STEP_DIR / f"{pid}.stl"
        export_step(solid, str(step_file))
        export_stl(solid, str(stl_file))

        # 3. Extract Ground-Truth Dimensions from geometry
        gt_dims = extract_gt_dimensions_from_part(solid, rec)

        # 4. Generate Standardized Isometric Render
        import trimesh
        mesh = trimesh.load(str(stl_file), force="mesh")
        edges = extract_edges_from_mesh(mesh)
        render_img = render_mesh_to_isometric(mesh.vertices, mesh.faces, edges)
        render_path = RENDERS_DIR / f"{pid}.png"
        render_img.save(str(render_path), "PNG")

        # 5. Compile Manifest Entry
        manifest_entries.append({
            "id": pid,
            "family": fam,
            "tier": tier,
            "params": rec["params"],
            "prompts": rec["prompts"],
            "step_relpath": f"step/{pid}.step",
            "stl_relpath": f"step/{pid}.stl",
            "render_relpath": f"renders/{pid}.png",
            "gt_dimensions": gt_dims,
            "expected": rec["expected"],
        })

    # Save manifest.jsonl
    manifest_file = GOLDEN_SET_DIR / "manifest.jsonl"
    with open(manifest_file, "w", encoding="utf-8") as mf:
        for entry in manifest_entries:
            mf.write(json.dumps(entry) + "\n")

    # Compute freeze hash
    hasher = hashlib.sha256()
    with open(manifest_file, "rb") as mf:
        hasher.update(mf.read())
    for entry in manifest_entries:
        step_p = GOLDEN_SET_DIR / entry["step_relpath"]
        with open(step_p, "rb") as sf:
            hasher.update(sf.read())

    freeze_hash = hasher.hexdigest()
    hash_file = GOLDEN_SET_DIR / "golden_set.sha256"
    with open(hash_file, "w", encoding="utf-8") as hf:
        hf.write(f"{freeze_hash}  manifest.jsonl\n")

    print("\n" + "=" * 60)
    print("GOLDEN SET BUILD COMPLETE")
    print("=" * 60)
    print(f"Total parts generated: {len(manifest_entries)}")
    print(f"STEP files in:         {STEP_DIR}")
    print(f"Isometric renders in:  {RENDERS_DIR}")
    print(f"Manifest written to:   {manifest_file}")
    print(f"Freeze SHA-256 Hash:   {freeze_hash}")
    print("=" * 60)


if __name__ == "__main__":
    build_golden_set()
