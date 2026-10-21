"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_m12
Design Brief: Create a 140 × 100 × 8 mm plate with a centred raised motor register Ø70 mm × 5 mm high and a Ø35 mm central clearance hole. Add four Ø9 mm mounting holes on a 105 × 70 mm rectangular pattern. Reinforce the underside with four ribs 6 mm thick and 18 mm tall, arranged as two orthogonal pairs without blocking the mounting holes. Fuse ribs and plate into one solid.
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
Generated build123d code for CADIR Document: Create 140 100 (ID: doc_eval_m12)
Component Family: plate, Units: mm
"""

with BuildPart() as p:
    # Feature: Lid Main Plate (box)
    Box(length=140.0, width=100.0, height=8.0, mode=Mode.ADD)

    # Feature: Underside Stepped Rim (box)
    with Locations((0.0, 0.0, -6.0)):
        Box(length=132.0, width=92.0, height=4.0, mode=Mode.ADD)

    # Feature: Mounting Hole 1 (hole)
    with Locations((53.2, 35.0, 0.0)):
        CounterBoreHole(radius=2.5, counter_bore_radius=4.5, counter_bore_depth=3.0, depth=16.0)

    # Feature: Mounting Hole 2 (hole)
    with Locations((-53.2, 35.0, 0.0)):
        CounterBoreHole(radius=2.5, counter_bore_radius=4.5, counter_bore_depth=3.0, depth=16.0)

    # Feature: Mounting Hole 3 (hole)
    with Locations((53.2, -35.0, 0.0)):
        CounterBoreHole(radius=2.5, counter_bore_radius=4.5, counter_bore_depth=3.0, depth=16.0)

    # Feature: Mounting Hole 4 (hole)
    with Locations((-53.2, -35.0, 0.0)):
        CounterBoreHole(radius=2.5, counter_bore_radius=4.5, counter_bore_depth=3.0, depth=16.0)

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
