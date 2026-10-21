"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_m22
Design Brief: Create a base housing 100 × 70 × 18 mm and a separate cap 100 × 70 × 12 mm. Together they enclose a cylindrical cavity Ø40 mm along the 100 mm axis. Add four M8 nominal clearance holes (Ø9 mm) through the cap and matching threaded-hole pilot bores Ø6.8 mm in the base. Add two Ø6 mm dowel holes at diagonally opposite positions, aligned between the two halves. Export the two parts as separate solids and as an assembled STEP.
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
Generated build123d code for CADIR Document: Create Base Housing 100 (ID: doc_eval_m22)
Component Family: housing, Units: mm
"""

with BuildPart() as p:
    # Feature: Housing Body (cylinder)
    Cylinder(radius=50.0, height=18.0, mode=Mode.ADD)

    # Feature: Bearing Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=35.0, depth=None)

    # Feature: Inner Fillet (fillet)
    try:
        _edges = p.edges()
        _edges = _edges.sort_by(Axis.Z)[:4]
        if _edges:
            fillet(_edges, radius=2.0)
    except Exception as _fe:
        print(f"Fillet warning: {_fe}")

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
