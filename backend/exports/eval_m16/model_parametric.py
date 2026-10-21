"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_m16
Design Brief: Create a 160 mm-long stepped shaft with sections Ø20 × 30 mm, Ø30 × 50 mm, Ø25 × 40 mm, and Ø16 × 40 mm. Add two bearing seats Ø25 mm, each 20 mm long, on the Ø25 section; add two 5 mm-wide × 2.5 mm-deep keyways on designated Ø30 and Ø25 seats, each 30 mm long. Include 1.5 mm shoulder fillets where space permits and 0.5 mm end chamfers. Keep all sections coaxial.
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
Generated build123d code for CADIR Document: Shaft D20.0x160.0mm (ID: doc_eval_m16)
Component Family: shaft, Units: mm
"""

with BuildPart() as p:
    # Feature: Main Section (cylinder)
    with Locations((0.0, 0.0, 15.0)):
        Cylinder(radius=10.0, height=30.0, mode=Mode.ADD)

    # Feature: Stepped Section (cylinder)
    with Locations((0.0, 0.0, 95.0)):
        Cylinder(radius=15.0, height=130.0, mode=Mode.ADD)

    # Feature: End Chamfer (chamfer)
    try:
        _edges = p.edges()
        _edges = _edges.sort_by(Axis.Z)[-4:]
        if _edges:
            chamfer(_edges, length=1.0)
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
