"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_m28
Design Brief: Create a 180 mm-long flat link 25 mm wide and 8 mm thick. Add a Ø12 mm hole at each end with centres 20 mm from each end. Cut a central longitudinal slot 70 mm overall length and 8 mm width, centred along the link. Add shallow 1 mm-deep relief pockets 18 × 15 mm near both ends. Maintain a minimum 5 mm ligament between slot edges and the side boundaries.
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
Generated build123d code for CADIR Document: Create 180 Mm-long Flat Link (ID: doc_eval_m28)
Component Family: custom_part, Units: mm
"""

with BuildPart() as p:
    # Feature: Base Plate (box)
    Box(length=180.0, width=25.0, height=8.0, mode=Mode.ADD)

    # Feature: Centre Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=3.125, depth=12.0)

    # Feature: Corner Hole 1 (hole)
    with Locations((62.99999999999999, 8.75, 0.0)):
        Hole(radius=1.5625, depth=12.0)

    # Feature: Corner Hole 2 (hole)
    with Locations((-62.99999999999999, 8.75, 0.0)):
        Hole(radius=1.5625, depth=12.0)

    # Feature: Corner Hole 3 (hole)
    with Locations((62.99999999999999, -8.75, 0.0)):
        Hole(radius=1.5625, depth=12.0)

    # Feature: Corner Hole 4 (hole)
    with Locations((-62.99999999999999, -8.75, 0.0)):
        Hole(radius=1.5625, depth=12.0)

    # Feature: Vertical Fillet (fillet)
    try:
        _edges = p.edges()
        _edges = _edges.filter_by(Axis.Z)
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
