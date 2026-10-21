"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_m14
Design Brief: Create a bearing sleeve with Ø50 mm OD, Ø30 mm bore, and 40 mm body length. Add an integral mounting flange Ø90 mm × 8 mm thick at one end. Cut four Ø9 mm holes on a Ø68 mm pitch circle through the flange. Add a 2 mm-deep retaining ring groove inside the bore, 6 mm from the non-flanged end, while keeping at least 2 mm wall thickness.
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
Generated build123d code for CADIR Document: Shaft D50.0x150.0mm (ID: doc_eval_m14)
Component Family: flange, Units: mm
"""

with BuildPart() as p:
    # Feature: Shaft Body (cylinder)
    Cylinder(radius=25.0, height=150.0, mode=Mode.ADD)

    # Feature: End Chamfer (chamfer)
    try:
        _edges = p.edges()
        _edges = _edges.sort_by(Axis.Z)[-4:]
        if _edges:
            chamfer(_edges, length=1.0)
    except Exception as _ce:
        print(f"Chamfer warning: {_ce}")

    # Feature: Circumferential Retaining Groove (groove)
    with BuildPart(mode=Mode.SUBTRACT):
        with Locations((0.0, 0.0, 69.0)):
            Cylinder(radius=26.0, height=1.5)
            Cylinder(radius=24.0, height=1.7, mode=Mode.SUBTRACT)

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
