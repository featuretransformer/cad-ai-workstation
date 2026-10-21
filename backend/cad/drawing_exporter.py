"""
Automated 2D Engineering Drawing Sheet Generator.
Generates multi-view engineering technical drawing sheets (PNG/PDF)
with isometric 3D views, orthographic projections (Top, Front, Side),
bounding envelopes, and a professional engineering title block.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


def generate_drawing_sheet(
    mesh_or_stl_path: Any,
    design_id: str,
    title: str = "Mechanical Component",
    specs: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> Optional[str]:
    """
    Renders an engineering drawing sheet with 4 panels:
    - Panel 1: Shaded 3D Isometric View
    - Panel 2: Top Plan View (X-Y)
    - Panel 3: Front Elevation View (X-Z)
    - Panel 4: Right Side Elevation View (Y-Z)
    Plus dimension tags and title block.
    """
    try:
        import trimesh
        if isinstance(mesh_or_stl_path, (str, Path)):
            stl_p = Path(mesh_or_stl_path)
            if not stl_p.exists():
                return None
            mesh = trimesh.load(str(stl_p), force="mesh")
        else:
            mesh = mesh_or_stl_path

        if mesh is None or (hasattr(mesh, "is_empty") and mesh.is_empty):
            return None

        specs = specs or {}
        vol = round(float(getattr(mesh, "volume", 0.0)), 1)
        bounds = mesh.bounds
        dx = round(float(bounds[1][0] - bounds[0][0]), 1)
        dy = round(float(bounds[1][1] - bounds[0][1]), 1)
        dz = round(float(bounds[1][2] - bounds[0][2]), 1)

        fig = plt.figure(figsize=(16, 9), dpi=150, facecolor="#0a0f1d")

        # Styling tokens
        plt.rcParams["text.color"] = "#f1f5f9"
        plt.rcParams["axes.labelcolor"] = "#94a3b8"
        plt.rcParams["xtick.color"] = "#64748b"
        plt.rcParams["ytick.color"] = "#64748b"

        # Super Header
        fig.suptitle(
            f"ENGINEERING TECHNICAL DRAWING SHEET — {title.upper()}",
            fontsize=15,
            fontweight="bold",
            color="#38bdf8",
            y=0.97,
        )

        # ----------------------------------------------------------------------
        # Subplot 1: 3D Isometric View (Top-Left)
        # ----------------------------------------------------------------------
        ax_iso = fig.add_subplot(2, 2, 1, projection="3d", facecolor="#070c18")
        ax_iso.set_title("3D Isometric View", color="#38bdf8", fontsize=11, pad=8)

        vertices = mesh.vertices
        faces = mesh.faces
        triangles = vertices[faces]

        mesh_collection = Poly3DCollection(
            triangles,
            alpha=0.90,
            facecolor="#0284c7",
            edgecolor="#38bdf8",
            linewidths=0.25,
        )
        ax_iso.add_collection3d(mesh_collection)

        center = (bounds[0] + bounds[1]) / 2.0
        max_range = max(dx, dy, dz) / 1.7
        ax_iso.set_xlim(center[0] - max_range, center[0] + max_range)
        ax_iso.set_ylim(center[1] - max_range, center[1] + max_range)
        ax_iso.set_zlim(center[2] - max_range, center[2] + max_range)
        ax_iso.view_init(elev=28, azim=45)
        ax_iso.set_xlabel("X (mm)", labelpad=-6, fontsize=8)
        ax_iso.set_ylabel("Y (mm)", labelpad=-6, fontsize=8)
        ax_iso.set_zlabel("Z (mm)", labelpad=-6, fontsize=8)
        ax_iso.tick_params(labelsize=7)

        # ----------------------------------------------------------------------
        # Subplot 2: Top Plan View (X-Y) (Top-Right)
        # ----------------------------------------------------------------------
        ax_top = fig.add_subplot(2, 2, 2, facecolor="#070c18")
        ax_top.set_title(f"Top Plan View (X-Y) — {dx} mm x {dy} mm", color="#38bdf8", fontsize=11, pad=8)
        ax_top.scatter(vertices[:, 0], vertices[:, 1], s=0.2, c="#38bdf8", alpha=0.4)
        ax_top.axhline(0, color="#475569", linestyle="--", linewidth=0.6)
        ax_top.axvline(0, color="#475569", linestyle="--", linewidth=0.6)
        ax_top.set_xlabel("X (mm)", fontsize=9)
        ax_top.set_ylabel("Y (mm)", fontsize=9)
        ax_top.set_aspect("equal", adjustable="datalim")
        ax_top.grid(True, linestyle=":", alpha=0.3, color="#334155")
        ax_top.tick_params(labelsize=8)

        # ----------------------------------------------------------------------
        # Subplot 3: Front Elevation View (X-Z) (Bottom-Left)
        # ----------------------------------------------------------------------
        ax_front = fig.add_subplot(2, 2, 3, facecolor="#070c18")
        ax_front.set_title(f"Front Elevation (X-Z) — Height: {dz} mm", color="#38bdf8", fontsize=11, pad=8)
        ax_front.scatter(vertices[:, 0], vertices[:, 2], s=0.2, c="#06b6d4", alpha=0.4)
        ax_front.axhline(0, color="#475569", linestyle="--", linewidth=0.6)
        ax_front.axvline(0, color="#475569", linestyle="--", linewidth=0.6)
        ax_front.set_xlabel("X (mm)", fontsize=9)
        ax_front.set_ylabel("Z (mm)", fontsize=9)
        ax_front.set_aspect("equal", adjustable="datalim")
        ax_front.grid(True, linestyle=":", alpha=0.3, color="#334155")
        ax_front.tick_params(labelsize=8)

        # ----------------------------------------------------------------------
        # Subplot 4: Right Side Elevation (Y-Z) (Bottom-Right)
        # ----------------------------------------------------------------------
        ax_side = fig.add_subplot(2, 2, 4, facecolor="#070c18")
        ax_side.set_title(f"Side Elevation (Y-Z) — Width: {dy} mm", color="#38bdf8", fontsize=11, pad=8)
        ax_side.scatter(vertices[:, 1], vertices[:, 2], s=0.2, c="#0ea5e9", alpha=0.4)
        ax_side.axhline(0, color="#475569", linestyle="--", linewidth=0.6)
        ax_side.axvline(0, color="#475569", linestyle="--", linewidth=0.6)
        ax_side.set_xlabel("Y (mm)", fontsize=9)
        ax_side.set_ylabel("Z (mm)", fontsize=9)
        ax_side.set_aspect("equal", adjustable="datalim")
        ax_side.grid(True, linestyle=":", alpha=0.3, color="#334155")
        ax_side.tick_params(labelsize=8)

        # Title Block Banner at Bottom
        info_text = (
            f"DESIGN ID: {design_id[:16]}... | "
            f"ENVELOPE: {dx} x {dy} x {dz} mm | "
            f"VOLUME: {vol:,} mm³ | "
            f"PROJECTION: 3rd Angle (ISO) | "
            f"TOLERANCE: ISO 2768-m"
        )
        fig.text(
            0.5,
            0.02,
            info_text,
            ha="center",
            fontsize=9,
            color="#94a3b8",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#0f172a", edgecolor="#38bdf8", alpha=0.85),
        )

        plt.tight_layout(rect=[0.02, 0.04, 0.98, 0.94])

        target_out = output_path
        if not target_out:
            if isinstance(mesh_or_stl_path, (str, Path)):
                target_out = str(Path(mesh_or_stl_path).parent / "drawing_sheet.png")
            else:
                target_out = f"drawing_sheet_{design_id[:8]}.png"

        Path(target_out).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(target_out, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

        return target_out

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Could not generate drawing sheet: %s", e)
        return None
