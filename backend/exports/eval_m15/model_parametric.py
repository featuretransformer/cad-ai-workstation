"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_m15
Design Brief: Model a simplified folded enclosure made from 2 mm-thick sheet geometry, external dimensions 180 × 120 × 80 mm, open at the front. Add four 15 mm-deep inward mounting returns at the front edges, each with Ø5 mm holes. Include a separate 2 mm-thick removable front cover with six matching holes. Keep enclosure body and cover separate and make their mating perimeter align without interference.
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
Generated build123d code for CADIR Document: Model Simplified Folded Enclosure Made (ID: doc_eval_m15)
Component Family: custom_part, Units: mm
"""

with BuildPart() as p:
    # Feature: Base Plate (box)
    Box(length=2.0, width=180.0, height=120.0, mode=Mode.ADD)

    # Feature: Centre Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=0.25, depth=None)

    # Feature: Corner Hole 1 (hole)
    with Locations((0.7, 62.99999999999999, 0.0)):
        Hole(radius=0.125, depth=None)

    # Feature: Corner Hole 2 (hole)
    with Locations((-0.7, 62.99999999999999, 0.0)):
        Hole(radius=0.125, depth=None)

    # Feature: Corner Hole 3 (hole)
    with Locations((0.7, -62.99999999999999, 0.0)):
        Hole(radius=0.125, depth=None)

    # Feature: Corner Hole 4 (hole)
    with Locations((-0.7, -62.99999999999999, 0.0)):
        Hole(radius=0.125, depth=None)

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
