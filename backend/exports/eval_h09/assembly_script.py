"""
Assembly: Automotive Disc Brake Assembly (ID: asm_brake_eval_h09)
Total Components: 5, Total Instances: 5
"""
from build123d import *

# === Component: Ventilated Brake Rotor Disc (comp_eval_h09_rotor) ===
"""
Generated build123d code for CADIR Document: Ventilated Brake Rotor Disc (ID: doc_comp_eval_h09_rotor)
Component Family: brake_rotor, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Ventilated Brake Rotor Disc Solid (cylinder)
    Cylinder(radius=70.0, height=16.0, mode=Mode.ADD)

    # Feature: Ventilated Brake Rotor Disc Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=22.5, depth=None)

result = p.part

# === Component: Brake Caliper Body (comp_eval_h09_caliper) ===
"""
Generated build123d code for CADIR Document: Brake Caliper Body (ID: doc_comp_eval_h09_caliper)
Component Family: caliper, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Brake Caliper Body Body (box)
    Box(length=85.0, width=60.0, height=45.0, mode=Mode.ADD)

    # Feature: Brake Caliper Body Cavity (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=16.0, depth=None)

result = p.part

# === Component: Inner Brake Friction Pad (comp_eval_h09_pad_in) ===
"""
Generated build123d code for CADIR Document: Inner Brake Friction Pad (ID: doc_comp_eval_h09_pad_in)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Inner Brake Friction Pad Plate (box)
    Box(length=45.0, width=30.0, height=6.0, mode=Mode.ADD)

result = p.part

# === Component: Outer Brake Friction Pad (comp_eval_h09_pad_out) ===
"""
Generated build123d code for CADIR Document: Outer Brake Friction Pad (ID: doc_comp_eval_h09_pad_out)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Outer Brake Friction Pad Plate (box)
    Box(length=45.0, width=30.0, height=6.0, mode=Mode.ADD)

result = p.part

# === Component: Caliper Torque Anchor Bracket (comp_eval_h09_bracket) ===
"""
Generated build123d code for CADIR Document: Caliper Torque Anchor Bracket (ID: doc_comp_eval_h09_bracket)
Component Family: bracket, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Caliper Torque Anchor Bracket Base (box)
    Box(length=75.0, width=35.0, height=10.0, mode=Mode.ADD)

    # Feature: Caliper Torque Anchor Bracket Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=5.25, depth=None)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 5 solids into Compound