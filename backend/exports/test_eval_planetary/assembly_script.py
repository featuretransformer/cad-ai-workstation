"""
Assembly: Epicyclic Planetary Gearbox Assembly (ID: asm_planetary_test1234)
Total Components: 4, Total Instances: 6
"""
from build123d import *

# === Component: Sun Gear (comp_test1234_sun) ===
"""
Generated build123d code for CADIR Document: Sun Gear (ID: doc_comp_test1234_sun)
Component Family: gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gear Blank Cylinder (cylinder)
    Cylinder(radius=12.0, height=15.0, mode=Mode.ADD)

    # Feature: Shaft Bore Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=5.0, depth=None)

result = p.part

# === Component: Planet Gear (comp_test1234_planet) ===
"""
Generated build123d code for CADIR Document: Planet Gear (ID: doc_comp_test1234_planet)
Component Family: gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gear Blank Cylinder (cylinder)
    Cylinder(radius=12.0, height=15.0, mode=Mode.ADD)

    # Feature: Shaft Bore Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.0, depth=None)

result = p.part

# === Component: Internal Ring Gear (comp_test1234_ring) ===
"""
Generated build123d code for CADIR Document: Internal Ring Gear (ID: doc_comp_test1234_ring)
Component Family: ring_gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Internal Ring Gear Solid (cylinder)
    Cylinder(radius=45.0, height=18.0, mode=Mode.ADD)

    # Feature: Internal Ring Gear Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=36.0, depth=None)

result = p.part

# === Component: Planet Carrier Plate (comp_test1234_carrier) ===
"""
Generated build123d code for CADIR Document: Planet Carrier Plate (ID: doc_comp_test1234_carrier)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Planet Carrier Plate Disk (cylinder)
    Cylinder(radius=35.0, height=8.0, mode=Mode.ADD)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 6 solids into Compound