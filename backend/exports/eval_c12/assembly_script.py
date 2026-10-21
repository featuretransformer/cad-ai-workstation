"""
Assembly: Epicyclic Planetary Gearbox Assembly (ID: asm_planetary_eval_c12)
Total Components: 5, Total Instances: 7
"""
from build123d import *

# === Component: Sun Drive Gear (comp_eval_c12_sun) ===
"""
Generated build123d code for CADIR Document: Sun Drive Gear (ID: doc_comp_eval_c12_sun)
Component Family: gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gear Blank Cylinder (cylinder)
    Cylinder(radius=14.0, height=18.0, mode=Mode.ADD)

    # Feature: Shaft Bore Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=6.0, depth=None)

result = p.part

# === Component: Planet Gear (comp_eval_c12_planet) ===
"""
Generated build123d code for CADIR Document: Planet Gear (ID: doc_comp_eval_c12_planet)
Component Family: gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gear Blank Cylinder (cylinder)
    Cylinder(radius=12.0, height=18.0, mode=Mode.ADD)

    # Feature: Shaft Bore Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.0, depth=None)

result = p.part

# === Component: Internal Annulus Ring Gear (comp_eval_c12_ring) ===
"""
Generated build123d code for CADIR Document: Internal Annulus Ring Gear (ID: doc_comp_eval_c12_ring)
Component Family: ring_gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Internal Annulus Ring Gear Solid (cylinder)
    Cylinder(radius=48.0, height=20.0, mode=Mode.ADD)

    # Feature: Internal Annulus Ring Gear Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=38.0, depth=None)

result = p.part

# === Component: Planet Carrier Flange (comp_eval_c12_carrier) ===
"""
Generated build123d code for CADIR Document: Planet Carrier Flange (ID: doc_comp_eval_c12_carrier)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Planet Carrier Flange Disk (cylinder)
    Cylinder(radius=37.5, height=8.0, mode=Mode.ADD)

result = p.part

# === Component: Carrier Output Shaft (comp_eval_c12_shaft) ===
"""
Generated build123d code for CADIR Document: Carrier Output Shaft (ID: doc_comp_eval_c12_shaft)
Component Family: shaft, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Carrier Output Shaft Shaft (cylinder)
    Cylinder(radius=7.0, height=65.0, mode=Mode.ADD)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 7 solids into Compound