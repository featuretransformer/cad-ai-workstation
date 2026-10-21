"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_m03
Design Brief: Model a 90° elbow with a constant Ø32 mm outside diameter and Ø24 mm inside diameter along a centreline bend radius of 48 mm. Provide 25 mm straight tangents at both ends. Add circular end collars of Ø44 mm OD and 8 mm axial thickness, each with two Ø6 mm bolt holes on a Ø34 mm pitch circle. Ensure the inner passage follows the bend and has no blocked openings or invalid self-intersections.
Kernel: build123d (OpenCASCADE Community Edition)
Units: millimeters (mm)
==============================================================================
INSTRUCTIONS FOR MECHANICAL ENGINEERS:
1. Modify any parameter in the "DESIGN VARIABLES" section below.
2. Run `python <filename>.py` to regenerate updated STEP and STL files.
==============================================================================
"""
import sys
from pathlib import Path
from build123d import *

# ============================================================================== #
#                        1. PARAMETRIC DESIGN VARIABLES                          #
# ============================================================================== #
OVERALL_SCALE            = 1.0         # mm

# ============================================================================== #
#                        2. GEOMETRIC CONSTRUCTION                               #
# ============================================================================== #

"""
Generated build123d code for CADIR Document: Model 90° Elbow With (ID: doc_eval_m03)
Component Family: bolt, Units: mm
"""

with BuildPart() as p:
    # Feature: Bolt Head (cylinder)
    Cylinder(radius=45.0, height=36.0, mode=Mode.ADD)

    # Feature: Bolt Shank (cylinder)
    with Locations((0.0, 0.0, -12.0)):
        Cylinder(radius=16.0, height=24.0, mode=Mode.ADD)

    # Feature: Lead Chamfer (chamfer)
    try:
        _edges = p.edges()
        _edges = _edges.sort_by(Axis.Z)[:4] 
        if _edges:
            chamfer(_edges, length=1.0)
    except Exception as _ce:
        print(f"Chamfer warning: {_ce}")

result = p.part

# ============================================================================== #
#                        3. EXECUTION & CAD EXPORT                               #
# ============================================================================== #
if __name__ == "__main__":
    # Find the resulting solid part or compound
    solid = None
    if "p" in locals() and hasattr(locals()["p"], "part"):
        solid = locals()["p"].part
    elif "assembly" in locals():
        solid = locals()["assembly"]
    elif "compound" in locals():
        solid = locals()["compound"]

    if solid is not None:
        out_dir = Path(__file__).resolve().parent
        step_file = out_dir / "output.step"
        stl_file = out_dir / "output.stl"
        
        export_step(solid, str(step_file))
        export_stl(solid, str(stl_file))
        
        vol = getattr(solid, "volume", 0.0)
        bbox = getattr(solid, "bounding_box", None)
        print("=" * 60)
        print("CAD MODEL GENERATED SUCCESSFULLY")
        print(f"Volume: {round(vol, 2)} mm^3")
        if bbox:
            print(f"Bounding Box: X=[{bbox().min.X:.1f}, {bbox().max.X:.1f}], Y=[{bbox().min.Y:.1f}, {bbox().max.Y:.1f}], Z=[{bbox().min.Z:.1f}, {bbox().max.Z:.1f}] mm")
        print(f"Exported STEP: {step_file.name}")
        print(f"Exported STL:  {stl_file.name}")
        print("=" * 60)
    else:
        print("Error: Could not locate constructed CAD solid.")
