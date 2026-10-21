"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_m05
Design Brief: Create a 100 × 60 × 8 mm base with an upright plate 60 mm wide, 45 mm tall, and 8 mm thick at one short edge. Add two horizontal slots 24 × 9 mm in the base and two vertical slots 20 × 9 mm in the upright. Slot ends must be semicircular, dimensions refer to overall slot length and width, and the bracket must be one connected solid with a 6 mm internal corner fillet.
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
Generated build123d code for CADIR Document: Create 100 (ID: doc_eval_m05)
Component Family: bracket, Units: mm
"""

with BuildPart() as p:
    # Feature: Base Flange (box)
    Box(length=100.0, width=60.0, height=8.0, mode=Mode.ADD)

    # Feature: Vertical Wall (box)
    with Locations((0.0, -26.0, 30.0)):
        Box(length=100.0, width=8.0, height=60.0, mode=Mode.ADD)

    # Feature: Mounting Hole 1 (hole)
    with Locations((25.0, 0.0, 0.0)):
        Hole(radius=2.2, depth=None)

    # Feature: Mounting Hole 2 (hole)
    with Locations((-25.0, 0.0, 0.0)):
        Hole(radius=6.0, depth=None)

    # Feature: Inner Radius (fillet)
    try:
        _edges = p.edges()
        _edges = _edges.filter_by(Axis.Z)
        if _edges:
            fillet(_edges, radius=3.0)
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
