"""
Assembly: Three-Finger Mechanical Gripper Assembly (ID: asm_gripper__test_01)
Total Components: 5, Total Instances: 11
"""
from build123d import *

# === Component: Base Mounting Plate (comp__test_01_mount_plate) ===
"""
Generated build123d code for CADIR Document: Base Mounting Plate (ID: doc_comp__test_01_mount_plate)
Component Family: mounting_plate, Units: mm
"""
from build123d import *
import math

# Step-by-step feature volume tracking list (Upgrade 3)
step_volumes = []

with BuildPart() as p:
    # Feature: Plate Base Disk (cylinder)
    Cylinder(radius=60.0, height=12.0, mode=Mode.ADD)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_base", "feature_type": "cylinder", "operation": "new_body", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_base", "feature_type": "cylinder", "operation": "new_body", "volume": 0.0})

    # Feature: Actuator Center Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=16.0, depth=None)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_center_bore", "feature_type": "hole", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_center_bore", "feature_type": "hole", "operation": "cut", "volume": 0.0})

    # Feature: Clevis Mounting Lug 1 (box)
    with Locations((45.0, 0.0, 21.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_lug_1", "feature_type": "box", "operation": "join", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_lug_1", "feature_type": "box", "operation": "join", "volume": 0.0})

    # Feature: Clevis Slot 1 (pocket)
    with Locations((45.0, 0.0, 22.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_clevis_slot_1", "feature_type": "pocket", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_clevis_slot_1", "feature_type": "pocket", "operation": "cut", "volume": 0.0})

    # Feature: Lug Pin Hole 1 (hole)
    with Locations((45.0, 0.0, 23.700000000000003)):
        Hole(radius=4.0, depth=30.0)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_pin_hole_1", "feature_type": "hole", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_pin_hole_1", "feature_type": "hole", "operation": "cut", "volume": 0.0})

    # Feature: Clevis Mounting Lug 2 (box)
    with Locations((-22.5, 38.97, 21.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_lug_2", "feature_type": "box", "operation": "join", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_lug_2", "feature_type": "box", "operation": "join", "volume": 0.0})

    # Feature: Clevis Slot 2 (pocket)
    with Locations((-22.5, 38.97, 22.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_clevis_slot_2", "feature_type": "pocket", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_clevis_slot_2", "feature_type": "pocket", "operation": "cut", "volume": 0.0})

    # Feature: Lug Pin Hole 2 (hole)
    with Locations((-22.5, 38.97, 23.700000000000003)):
        Hole(radius=4.0, depth=30.0)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_pin_hole_2", "feature_type": "hole", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_pin_hole_2", "feature_type": "hole", "operation": "cut", "volume": 0.0})

    # Feature: Clevis Mounting Lug 3 (box)
    with Locations((-22.5, -38.97, 21.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_lug_3", "feature_type": "box", "operation": "join", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_lug_3", "feature_type": "box", "operation": "join", "volume": 0.0})

    # Feature: Clevis Slot 3 (pocket)
    with Locations((-22.5, -38.97, 22.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_clevis_slot_3", "feature_type": "pocket", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_clevis_slot_3", "feature_type": "pocket", "operation": "cut", "volume": 0.0})

    # Feature: Lug Pin Hole 3 (hole)
    with Locations((-22.5, -38.97, 23.700000000000003)):
        Hole(radius=4.0, depth=30.0)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_nt_plate_pin_hole_3", "feature_type": "hole", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_nt_plate_pin_hole_3", "feature_type": "hole", "operation": "cut", "volume": 0.0})

result = p.part

# === Component: Articulated Gripping Finger (comp__test_01_finger) ===
"""
Generated build123d code for CADIR Document: Articulated Gripping Finger (ID: doc_comp__test_01_finger)
Component Family: finger, Units: mm
"""
from build123d import *
import math

# Step-by-step feature volume tracking list (Upgrade 3)
step_volumes = []

with BuildPart() as p:
    # Feature: Finger Beam Body (box)
    with Locations((27.5, 0.0, 5.0)):
        Box(length=75.0, width=16.0, height=10.0, mode=Mode.ADD)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_1_finger_body", "feature_type": "box", "operation": "new_body", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_1_finger_body", "feature_type": "box", "operation": "new_body", "volume": 0.0})

    # Feature: Main Hinge Pivot Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.0, depth=20.0)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_1_finger_pivot_hole", "feature_type": "hole", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_1_finger_pivot_hole", "feature_type": "hole", "operation": "cut", "volume": 0.0})

    # Feature: Linkage Drive Hole (hole)
    with Locations((22.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=20.0)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_1_finger_link_hole", "feature_type": "hole", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_1_finger_link_hole", "feature_type": "hole", "operation": "cut", "volume": 0.0})

    # Feature: Finger Tip Taper Pocket (pocket)
    with Locations((60.0, 0.0, 7.0)):
        Box(length=30.0, width=8.0, height=6.0, mode=Mode.SUBTRACT)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_1_finger_tip_taper", "feature_type": "pocket", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_1_finger_tip_taper", "feature_type": "pocket", "operation": "cut", "volume": 0.0})

result = p.part

# === Standard Reused Component: Finger Pivot Pin (comp__test_01_pivot_pin) ===
# Reused Standard Asset: Finger Pivot Pin
# Source: Curated ISO Standard Library
# License: CC0-1.0
part = import_step('C:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/datasets/cad_assets/models/iso_2338_pin_6x24.step')
# === Component: Actuation Drive Link (comp__test_01_linkage) ===
"""
Generated build123d code for CADIR Document: Actuation Drive Link (ID: doc_comp__test_01_linkage)
Component Family: linkage, Units: mm
"""
from build123d import *
import math

# Step-by-step feature volume tracking list (Upgrade 3)
step_volumes = []

with BuildPart() as p:
    # Feature: Link Arm Solid (box)
    with Locations((21.0, 0.0, 2.5)):
        Box(length=42.0, width=12.0, height=5.0, mode=Mode.ADD)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f__linkage_arm", "feature_type": "box", "operation": "new_body", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f__linkage_arm", "feature_type": "box", "operation": "new_body", "volume": 0.0})

    # Feature: Drive End Hole (hole)
    with Locations((6.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=10.0)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f__linkage_hole_in", "feature_type": "hole", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f__linkage_hole_in", "feature_type": "hole", "operation": "cut", "volume": 0.0})

    # Feature: Output End Hole (hole)
    with Locations((36.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=10.0)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f__linkage_hole_out", "feature_type": "hole", "operation": "cut", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f__linkage_hole_out", "feature_type": "hole", "operation": "cut", "volume": 0.0})

result = p.part

# === Component: Central Actuator & Crosshead (comp__test_01_actuator) ===
"""
Generated build123d code for CADIR Document: Central Actuator & Crosshead (ID: doc_comp__test_01_actuator)
Component Family: actuator, Units: mm
"""
from build123d import *
import math

# Step-by-step feature volume tracking list (Upgrade 3)
step_volumes = []

with BuildPart() as p:
    # Feature: Actuator Cylinder Body (cylinder)
    Cylinder(radius=15.0, height=65.0, mode=Mode.ADD)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_actuator_body", "feature_type": "cylinder", "operation": "new_body", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_actuator_body", "feature_type": "cylinder", "operation": "new_body", "volume": 0.0})

    # Feature: Piston Extension Rod (cylinder)
    with Locations((0.0, 0.0, 65.0)):
        Cylinder(radius=6.0, height=30.0, mode=Mode.ADD)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_actuator_rod", "feature_type": "cylinder", "operation": "join", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_actuator_rod", "feature_type": "cylinder", "operation": "join", "volume": 0.0})

    # Feature: Linkage Crosshead Hub (cylinder)
    with Locations((0.0, 0.0, 95.0)):
        Cylinder(radius=14.0, height=10.0, mode=Mode.ADD)
    try:
        _step_v = float(p.part.volume) if (hasattr(p, 'part') and p.part is not None) else 0.0
        step_volumes.append({"feature_id": "f_actuator_crosshead", "feature_type": "cylinder", "operation": "join", "volume": _step_v})
    except Exception:
        step_volumes.append({"feature_id": "f_actuator_crosshead", "feature_type": "cylinder", "operation": "join", "volume": 0.0})

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 11 solids into Compound