"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_c26
Design Brief: Create a filter housing with a cylindrical chamber Ø120 mm internal diameter and 180 mm internal height, a 10 mm-thick bolted lid and a bottom base. Add inlet and outlet ports Ø25 mm oriented tangentially at two different elevations, a removable filter cartridge Ø80 mm × 150 mm, and a central sealing stem Ø12 mm. Use eight lid fasteners on a Ø140 mm bolt circle and an annular gasket groove. Keep fluid volume connected around the cartridge as intended, with removable parts and no accidental blocked ports.
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
Generated build123d code for CADIR Document: Create Filter Housing With (ID: doc_eval_c26)
Component Family: bolt, Units: mm
"""

with BuildPart() as p:
    # Feature: Washer Body (extrude)
    with BuildSketch(Plane(origin=(0.0, 0.0, 0.0), z_dir=(0.0, 0.0, 1.0), x_dir=(1.0, 0.0, 0.0))):
        Circle(radius=60.0)
    extrude(amount=10.0, mode=Mode.ADD)

    # Feature: Centre Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=30.0, depth=None)

    # Feature: Edge Chamfer (chamfer)
    try:
        _edges = p.edges()
        _edges = _edges.sort_by(Axis.Z)[-4:]
        if _edges:
            chamfer(_edges, length=0.5)
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
