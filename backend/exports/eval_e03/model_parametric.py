"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_e03
Design Brief: Model a 120 × 80 × 8 mm rectangular plate. Add four Ø9 mm through-holes, with hole centres 12 mm from each adjacent edge. The hole pattern must be symmetric about both plate centre lines. Keep the top and bottom faces planar and create exactly one solid.
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
Generated build123d code for CADIR Document: Rectangular Mounting Plate (ID: doc_plate_120x80x8)
Component Family: plate, Units: mm
"""

with BuildPart() as p:
    # Feature: Base Plate (box)
    with Locations((0.0, 0.0, 4.0)):
        Box(length=120.0, width=80.0, height=8.0, mode=Mode.ADD)

    # Feature: Top-Left Hole (hole)
    with Locations((-48.0, 28.0, 8.0)):
        Hole(radius=4.5, depth=8.0)

    # Feature: Top-Right Hole (hole)
    with Locations((48.0, 28.0, 8.0)):
        Hole(radius=2.48, depth=8.0)

    # Feature: Bottom-Left Hole (hole)
    with Locations((-48.0, -28.0, 8.0)):
        Hole(radius=1.36, depth=8.0)

    # Feature: Bottom-Right Hole (hole)
    with Locations((48.0, -28.0, 8.0)):
        Hole(radius=0.75, depth=8.0)

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
