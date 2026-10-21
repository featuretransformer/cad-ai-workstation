"""
==============================================================================
AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT
Design ID: eval_c17
Design Brief: Design a compact CNC linear axis with a 400 × 100 × 12 mm base, two Ø16 mm linear guide rails spaced 70 mm apart, four bearing blocks, and a central ball-screw envelope Ø16 mm. Add a 100 × 80 × 20 mm moving carriage, end support blocks with coaxial screw seats, and a nut housing attached to the carriage. Provide 250 mm nominal travel and end-stop positions. Keep moving carriage and blocks aligned to the rails, represent the screw thread realistically if supported, and validate collision-free motion envelopes or clearly identify motion as unverified.
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
Generated build123d code for CADIR Document: Design Compact Cnc Linear Axis (ID: doc_eval_c17)
Component Family: nut, Units: mm
"""

with BuildPart() as p:
    # Feature: Washer Body (extrude)
    with BuildSketch(Plane(origin=(0.0, 0.0, 0.0), z_dir=(0.0, 0.0, 1.0), x_dir=(1.0, 0.0, 0.0))):
        Circle(radius=200.0)
    extrude(amount=12.0, mode=Mode.ADD)

    # Feature: Centre Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=50.0, depth=None)

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
