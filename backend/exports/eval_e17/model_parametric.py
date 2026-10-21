"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_e17
Design Brief: Create a handle knob comprising a Ø32 mm spherical outer head joined to a Ø12 mm cylindrical stem 25 mm long. Include a centred M8 nominal mounting bore 12 mm deep from the bottom of the stem, represented as a Ø6.8 mm pilot hole if helical threads are unsupported. Ensure the sphere and stem overlap sufficiently to form one solid.
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
Generated build123d code for CADIR Document: Create Handle Knob Comprising (ID: doc_eval_e17)
Component Family: custom_part, Units: mm
"""

with BuildPart() as p:
    # Feature: Lid Main Plate (box)
    Box(length=32.0, width=12.0, height=25.0, mode=Mode.ADD)

    # Feature: Underside Stepped Rim (box)
    with Locations((0.0, 0.0, -14.5)):
        Box(length=24.0, width=10.0, height=4.0, mode=Mode.ADD)

    # Feature: Mounting Hole 1 (hole)
    with Locations((12.16, 4.199999999999999, 0.0)):
        CounterBoreHole(radius=2.5, counter_bore_radius=4.5, counter_bore_depth=3.0, depth=50.0)

    # Feature: Mounting Hole 2 (hole)
    with Locations((-12.16, 4.199999999999999, 0.0)):
        CounterBoreHole(radius=2.5, counter_bore_radius=4.5, counter_bore_depth=3.0, depth=50.0)

    # Feature: Mounting Hole 3 (hole)
    with Locations((12.16, -4.199999999999999, 0.0)):
        CounterBoreHole(radius=2.5, counter_bore_radius=4.5, counter_bore_depth=3.0, depth=50.0)

    # Feature: Mounting Hole 4 (hole)
    with Locations((-12.16, -4.199999999999999, 0.0)):
        CounterBoreHole(radius=2.5, counter_bore_radius=4.5, counter_bore_depth=3.0, depth=50.0)

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
