"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_m18
Design Brief: Create a hollow Y-manifold with one inlet branch OD 40 mm/ID 30 mm and two outlet branches OD 32 mm/ID 24 mm. Use smooth branch junctions and centreline angles of ±35° relative to the inlet, with 50 mm straight lengths from each branch junction to the open ends. Add end flanges 8 mm thick with two Ø6 mm holes on a Ø46 mm pitch circle for the inlet and two Ø5.5 mm holes on a Ø38 mm pitch circle for each outlet. Validate that all three passages connect internally.
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
Generated build123d code for CADIR Document: Create Hollow Y-manifold With One (ID: doc_eval_m18)
Component Family: flange, Units: mm
"""

with BuildPart() as p:
    # Feature: Housing Body (cylinder)
    Cylinder(radius=20.0, height=32.0, mode=Mode.ADD)

    # Feature: Bearing Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=15.0, depth=None)

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
