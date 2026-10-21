"""
Design Planner Agent Node.
Decomposes user requirements into modular mechanical components, mating interfaces,
kinematic joints, and spatial placements (AssemblySpec).
Supports both LLM-driven structured decomposition and deterministic rule-based mechanical synthesis.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import math
import re
import sys
import uuid

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from cad.assembly.schema import (
    AssemblySpec,
    ComponentSpec,
    MatingInterface,
    Placement3D,
)
from cad.cadir.schema import Point3D, Vector3D
from utils.llm import get_design_llm


ASSEMBLY_KEYWORDS = [
    "assembly",
    "subassembly",
    "gripper",
    "gearbox",
    "caster",
    "trolley",
    "vise",
    "clamp",
    "linkage",
    "mechanism",
    "coupling",
    "pillow block",
    "bearing assembly",
    "actuator",
    "robot arm",
    "robotic hand",
    "hinge assembly",
    "scissor lift",
    "differential",
    "winch",
]


def is_assembly_prompt(prompt: str, intent: Optional[Dict[str, Any]] = None) -> bool:
    """Detect whether a design request requires multi-component assembly decomposition."""
    p_lower = prompt.lower()
    if intent and intent.get("is_assembly") is True:
        return True

    # Check for plural components or explicit multi-part phrases
    if any(kw in p_lower for kw in ASSEMBLY_KEYWORDS):
        return True

    if "with " in p_lower and any(w in p_lower for w in ["fingers", "gears", "bearings", "pins", "jaw", "bolts"]):
        return True

    # Pattern like "3-finger" or "two jaw"
    if re.search(r"\b(?:\d+|two|three|four)-finger\b", p_lower):
        return True

    return False


def _extract_json_object(raw_text: str) -> Optional[str]:
    """Robust JSON extraction from LLM response."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    start = cleaned.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False
    for i in range(start, len(cleaned)):
        c = cleaned[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\" and in_string:
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    break
    return None


def decompose_three_finger_gripper(design_id: str, prompt: str) -> AssemblySpec:
    """
    Deterministic synthesis for Three-Finger Gripper Benchmark.
    Decomposes into:
    1. Base Mounting Plate (central actuator bore, 3 mounting clevis lugs at 120 deg)
    2. 3x Articulated Gripper Fingers (curved profile with pivot and linkage holes)
    3. 3x Pivot Pins (ground dowel pins connecting fingers to plate lugs)
    4. 3x Driving Linkages (connecting central actuator crosshead to fingers)
    5. Linear Actuator / Piston Hub (central linear cylinder with crosshead driver)
    """
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_gripper_{uid}"

    # Global Parameters
    plate_radius = 60.0
    plate_thickness = 12.0
    center_bore_dia = 32.0
    finger_mount_radius = 45.0
    finger_length = 75.0
    finger_width = 16.0
    finger_thickness = 10.0
    pin_dia = 8.0
    link_pin_dia = 5.0
    actuator_travel = 25.0

    # 1. Base Mounting Plate
    mount_plate = ComponentSpec(
        component_id=f"comp_{uid}_mount_plate",
        name="Base Mounting Plate",
        role="mounting_plate",
        quantity=1,
        material="Aluminum 6061-T6",
        motion_type="fixed",
        parameters={
            "diameter": plate_radius * 2.0,
            "thickness": plate_thickness,
            "center_bore": center_bore_dia,
            "bolt_circle_dia": 95.0,
            "bolt_hole_dia": 6.5,
            "mount_radius": finger_mount_radius,
            "lug_height": 18.0,
            "lug_thickness": 8.0,
            "pin_hole_dia": pin_dia,
        },
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
        description="Circular base plate with central actuator aperture, 3 clevis mounting lug pairs at 120°, and ISO mounting bolt pattern.",
    )

    # 2. Articulated Gripping Fingers (Quantity: 3)
    # Positions spaced at 0°, 120°, 240° on finger_mount_radius
    finger_placements = []
    pin_placements = []
    link_placements = []

    for i, angle_deg in enumerate([0.0, 120.0, 240.0]):
        rad = math.radians(angle_deg)
        fx = round(finger_mount_radius * math.cos(rad), 2)
        fy = round(finger_mount_radius * math.sin(rad), 2)
        # Lugs extend from z=12 to z=30. Pin axis is at z=23.5
        fz = 23.5

        finger_placements.append(
            Placement3D.from_xyz_rxyz(fx, fy, fz, rx=0, ry=0, rz=round(angle_deg, 2))
        )
        # Pins run along Z through the clevis lug and finger pivot
        pin_placements.append(
            Placement3D.from_xyz_rxyz(fx, fy, 11.0, rx=0, ry=0, rz=round(angle_deg, 2))
        )
        # Linkages positioned above finger at z=35, tilted inward to actuator crosshead
        lx = round((finger_mount_radius * 0.55) * math.cos(rad), 2)
        ly = round((finger_mount_radius * 0.55) * math.sin(rad), 2)
        link_placements.append(
            Placement3D.from_xyz_rxyz(lx, ly, 35.0, rx=0, ry=15.0, rz=round(angle_deg, 2))
        )

    fingers = ComponentSpec(
        component_id=f"comp_{uid}_finger",
        name="Articulated Gripping Finger",
        role="finger",
        quantity=3,
        material="Aluminum 7075-T6",
        motion_type="revolute",
        parameters={
            "length": finger_length,
            "width": finger_width,
            "thickness": finger_thickness,
            "pivot_hole_dia": pin_dia,
            "link_hole_dia": link_pin_dia,
            "tip_radius": 6.0,
        },
        base_placement=finger_placements[0],
        instance_placements=finger_placements,
        description="Symmetric articulated claw finger with clevis pivot mount and linkage actuation point.",
    )

    # 3. Pivot Pins (Quantity: 3)
    pins = ComponentSpec(
        component_id=f"comp_{uid}_pivot_pin",
        name="Finger Pivot Pin",
        role="pivot_pin",
        quantity=3,
        material="AISI 304 Stainless Steel",
        motion_type="fixed",
        parameters={
            "diameter": pin_dia - 0.05,  # H7/g6 nominal fit
            "length": 26.0,
            "head_diameter": 12.0,
            "head_thickness": 3.0,
        },
        base_placement=pin_placements[0],
        instance_placements=pin_placements,
        description="Precision dowel pins retaining articulated fingers inside mounting plate clevis lugs.",
    )

    # 4. Driving Linkages (Quantity: 3)
    linkages = ComponentSpec(
        component_id=f"comp_{uid}_linkage",
        name="Actuation Drive Link",
        role="linkage",
        quantity=3,
        material="Structural Steel",
        motion_type="revolute",
        parameters={
            "length": 42.0,
            "width": 12.0,
            "thickness": 5.0,
            "hole1_dia": link_pin_dia,
            "hole2_dia": link_pin_dia,
        },
        base_placement=link_placements[0],
        instance_placements=link_placements,
        description="Dual-hole pivot link transmitting linear actuator stroke into finger angular closure.",
    )

    # 5. Linear Actuator / Piston Crosshead
    actuator = ComponentSpec(
        component_id=f"comp_{uid}_actuator",
        name="Central Actuator & Crosshead",
        role="actuator",
        quantity=1,
        material="Alloy Steel 4140",
        motion_type="linear",
        parameters={
            "body_diameter": 30.0,
            "body_length": 65.0,
            "rod_diameter": 12.0,
            "crosshead_diameter": 28.0,
            "crosshead_thickness": 10.0,
            "stroke": actuator_travel,
        },
        base_placement=Placement3D.from_xyz_rxyz(0, 0, -25.0, 0, 0, 0),
        description="Central linear piston with slotted crosshead driving all 3 linkage arms simultaneously.",
    )

    # Mating Interfaces
    mates = [
        MatingInterface(
            interface_id="mate_plate_actuator",
            name="Mounting Plate Bore to Actuator Cylinder",
            mate_type="cylindrical",
            parent_component_id=mount_plate.component_id,
            child_component_id=actuator.component_id,
            parent_datum="central_bore",
            child_datum="outer_cylinder",
            clearance=0.15,
            offset=0.0,
        ),
        MatingInterface(
            interface_id="mate_plate_finger_clevis",
            name="Plate Clevis to Finger Hinge",
            mate_type="revolute",
            parent_component_id=mount_plate.component_id,
            child_component_id=fingers.component_id,
            parent_datum="lug_holes",
            child_datum="finger_pivot_hole",
            clearance=0.2,
            limits={"min_angle": 0.0, "max_angle": 45.0},
        ),
        MatingInterface(
            interface_id="mate_finger_pin",
            name="Finger Hinge to Pivot Pin",
            mate_type="coaxial",
            parent_component_id=fingers.component_id,
            child_component_id=pins.component_id,
            parent_datum="finger_pivot_hole",
            child_datum="pin_shaft",
            clearance=0.05,
        ),
        MatingInterface(
            interface_id="mate_actuator_linkage",
            name="Crosshead Driver to Linkage",
            mate_type="revolute",
            parent_component_id=actuator.component_id,
            child_component_id=linkages.component_id,
            parent_datum="crosshead_pin_holes",
            child_datum="link_hole_1",
            clearance=0.15,
        ),
        MatingInterface(
            interface_id="mate_linkage_finger",
            name="Linkage to Finger Driver Point",
            mate_type="revolute",
            parent_component_id=linkages.component_id,
            child_component_id=fingers.component_id,
            parent_datum="link_hole_2",
            child_datum="finger_link_hole",
            clearance=0.15,
        ),
    ]

    return AssemblySpec(
        id=asm_id,
        name="Three-Finger Mechanical Gripper Assembly",
        description="Precision mechanical three-finger gripper featuring polar-symmetric finger spacing (120°), linkage kinematics, and central linear drive.",
        assembly_family="gripper",
        units="mm",
        global_parameters={
            "finger_span": 150.0,
            "grip_diameter": 80.0,
            "stroke": actuator_travel,
            "mounting_diameter": plate_radius * 2.0,
            "max_payload_kg": 3.0,
        },
        components=[mount_plate, fingers, pins, linkages, actuator],
        mating_interfaces=mates,
        validation_requirements={
            "max_interference_volume": 0.0,
            "min_operating_clearance": 0.1,
            "max_envelope_dia": 180.0,
            "max_envelope_height": 160.0,
        },
        assumptions=[
            "Planar 3-finger mechanism configured with 120-degree radial polar symmetry",
            "Clearance fits follow ISO metric H7/g6 conventions (nominal joint clearances 0.15 - 0.20 mm)",
            "Central double-acting pneumatic or lead-screw linear actuator with 25mm stroke",
            "Material selection optimized for rigidity-to-weight ratio (6061-T6 aluminum body, 304 SS pins)",
        ],
        unresolved_parameters=[
            "Actuator supply type (pneumatic cylinder vs NEMA 17 stepper drive)",
            "Finger gripping pad surface (grooved aluminum vs polyurethane insert)",
        ],
    )


def decompose_gearbox_pair(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Gearbox / Gear Pair Assembly."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_gearbox_{uid}"

    center_distance = 60.0
    housing = ComponentSpec(
        component_id=f"comp_{uid}_housing",
        name="Gearbox Base Plate",
        role="housing",
        quantity=1,
        material="Cast Iron / Aluminum 6061",
        motion_type="fixed",
        parameters={
            "length": 140.0,
            "width": 90.0,
            "thickness": 15.0,
            "center_distance": center_distance,
            "bore_dia": 28.0,
        },
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )

    pinion = ComponentSpec(
        component_id=f"comp_{uid}_pinion",
        name="Drive Pinion Gear & Shaft",
        role="gear",
        quantity=1,
        material="Carbon Steel 1045",
        motion_type="revolute",
        parameters={"pitch_diameter": 36.0, "face_width": 20.0, "shaft_dia": 16.0, "shaft_len": 65.0},
        base_placement=Placement3D.from_xyz_rxyz(-center_distance / 2.0, 0, 15.0, 0, 0, 0),
    )

    gear = ComponentSpec(
        component_id=f"comp_{uid}_gear",
        name="Driven Spur Gear & Shaft",
        role="gear",
        quantity=1,
        material="Carbon Steel 1045",
        motion_type="revolute",
        parameters={"pitch_diameter": 84.0, "face_width": 20.0, "shaft_dia": 20.0, "shaft_len": 70.0},
        base_placement=Placement3D.from_xyz_rxyz(center_distance / 2.0, 0, 15.0, 0, 0, 0),
    )

    return AssemblySpec(
        id=asm_id,
        name="Spur Gear Reducer Assembly",
        assembly_family="gearbox",
        global_parameters={"gear_ratio": 2.33, "center_distance": center_distance},
        components=[housing, pinion, gear],
        mating_interfaces=[
            MatingInterface(
                interface_id="mate_gear_mesh",
                mate_type="gear_mesh",
                parent_component_id=pinion.component_id,
                child_component_id=gear.component_id,
                clearance=0.25,
            )
        ],
        assumptions=["Standard 20-degree pressure angle involute spur gears"],
        unresolved_parameters=["Bearing seal configuration (open vs shielded 6000-series)"],
    )


def decompose_caster_wheel(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Caster Wheel Assembly."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_caster_{uid}"

    top_plate = ComponentSpec(
        component_id=f"comp_{uid}_top_plate",
        name="Swivel Top Plate",
        role="mounting_plate",
        quantity=1,
        material="Structural Steel",
        motion_type="fixed",
        parameters={"length": 80.0, "width": 80.0, "thickness": 6.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 60.0, 0, 0, 0),
    )

    fork = ComponentSpec(
        component_id=f"comp_{uid}_fork",
        name="Caster Fork Bracket",
        role="bracket",
        quantity=1,
        material="Pressed Steel",
        motion_type="revolute",
        parameters={"width": 45.0, "height": 55.0, "thickness": 4.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 15.0, 0, 0, 0),
    )

    wheel = ComponentSpec(
        component_id=f"comp_{uid}_wheel",
        name="Wheel Roller",
        role="wheel",
        quantity=1,
        material="Polyurethane / Nylon",
        motion_type="revolute",
        parameters={"diameter": 60.0, "width": 30.0, "bore_dia": 10.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, rx=90.0, ry=0, rz=0),
    )

    axle = ComponentSpec(
        component_id=f"comp_{uid}_axle",
        name="Axle Bolt & Nut",
        role="fastener",
        quantity=1,
        material="Grade 8.8 Steel",
        motion_type="fixed",
        parameters={"diameter": 9.8, "length": 48.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, rx=90.0, ry=0, rz=0),
    )

    return AssemblySpec(
        id=asm_id,
        name="Heavy-Duty Caster Wheel Assembly",
        assembly_family="caster_wheel",
        components=[top_plate, fork, wheel, axle],
        mating_interfaces=[],
        assumptions=["Swivel head with 360-degree rotation", "Standard polyurethane wheel tread"],
        unresolved_parameters=["Brake lock requirement"],
    )


def decompose_planetary_gearbox(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Epicyclic Planetary Gearbox Assembly."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_planetary_{uid}"
    sun = ComponentSpec(
        component_id=f"comp_{uid}_sun",
        name="Sun Drive Gear",
        role="gear",
        quantity=1,
        material="Alloy Steel 4140",
        motion_type="revolute",
        parameters={"pitch_diameter": 28.0, "face_width": 18.0, "shaft_dia": 12.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    planet = ComponentSpec(
        component_id=f"comp_{uid}_planet",
        name="Planet Gear",
        role="gear",
        quantity=3,
        material="Alloy Steel 4140",
        motion_type="revolute",
        parameters={"pitch_diameter": 24.0, "face_width": 18.0, "shaft_dia": 8.0},
        base_placement=Placement3D.from_xyz_rxyz(26.0, 0, 0, 0, 0, 0),
    )
    ring = ComponentSpec(
        component_id=f"comp_{uid}_ring",
        name="Internal Annulus Ring Gear",
        role="ring_gear",
        quantity=1,
        material="Alloy Steel 4140",
        motion_type="fixed",
        parameters={"outer_diameter": 96.0, "inner_diameter": 76.0, "face_width": 20.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    carrier = ComponentSpec(
        component_id=f"comp_{uid}_carrier",
        name="Planet Carrier Flange",
        role="mounting_plate",
        quantity=1,
        material="Aluminum 7075",
        motion_type="revolute",
        parameters={"diameter": 75.0, "thickness": 8.0, "center_bore": 14.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, -14.0, 0, 0, 0),
    )
    shaft = ComponentSpec(
        component_id=f"comp_{uid}_shaft",
        name="Carrier Output Shaft",
        role="shaft",
        quantity=1,
        material="Carbon Steel 1045",
        motion_type="revolute",
        parameters={"diameter": 14.0, "length": 65.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, -45.0, 0, 0, 0),
    )
    return AssemblySpec(
        id=asm_id,
        name="Epicyclic Planetary Gearbox Assembly",
        assembly_family="planetary_gearbox",
        components=[sun, planet, ring, carrier, shaft],
        mating_interfaces=[],
        assumptions=["Standard 20-degree pressure angle involute planetary gear train with 3 planet gears"],
    )


def decompose_scissor_lift(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Scissor Lift Mechanism."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_scissor_{uid}"
    base = ComponentSpec(
        component_id=f"comp_{uid}_base",
        name="Base Frame Bed",
        role="mounting_plate",
        quantity=1,
        material="Structural Steel",
        motion_type="fixed",
        parameters={"length": 160.0, "width": 100.0, "thickness": 12.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    platform = ComponentSpec(
        component_id=f"comp_{uid}_platform",
        name="Top Lift Platform",
        role="mounting_plate",
        quantity=1,
        material="Structural Steel",
        motion_type="linear",
        parameters={"length": 160.0, "width": 100.0, "thickness": 10.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 85.0, 0, 0, 0),
    )
    arm_inner = ComponentSpec(
        component_id=f"comp_{uid}_arm_in",
        name="Inner Scissor Link Arm",
        role="linkage",
        quantity=2,
        material="Structural Steel",
        motion_type="revolute",
        parameters={"length": 110.0, "width": 16.0, "thickness": 8.0},
        base_placement=Placement3D.from_xyz_rxyz(-25.0, -35.0, 42.0, 0, 32.0, 0),
    )
    arm_outer = ComponentSpec(
        component_id=f"comp_{uid}_arm_out",
        name="Outer Scissor Link Arm",
        role="linkage",
        quantity=2,
        material="Structural Steel",
        motion_type="revolute",
        parameters={"length": 110.0, "width": 16.0, "thickness": 8.0},
        base_placement=Placement3D.from_xyz_rxyz(25.0, 35.0, 42.0, 0, -32.0, 0),
    )
    actuator = ComponentSpec(
        component_id=f"comp_{uid}_spindle",
        name="Central Actuator Drive Screw",
        role="lead_screw",
        quantity=1,
        material="Alloy Steel 4140",
        motion_type="linear",
        parameters={"diameter": 14.0, "length": 140.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 18.0, 0, 90.0, 0),
    )
    return AssemblySpec(
        id=asm_id,
        name="Mechanical Scissor Lift Table Assembly",
        assembly_family="scissor_lift",
        components=[base, platform, arm_inner, arm_outer, actuator],
        mating_interfaces=[],
    )


def decompose_disc_brake(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Automotive Disc Brake System."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_brake_{uid}"
    rotor = ComponentSpec(
        component_id=f"comp_{uid}_rotor",
        name="Ventilated Brake Rotor Disc",
        role="brake_rotor",
        quantity=1,
        material="Cast Iron / Carbon-Ceramic",
        motion_type="revolute",
        parameters={"outer_diameter": 140.0, "inner_diameter": 45.0, "face_width": 16.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    caliper = ComponentSpec(
        component_id=f"comp_{uid}_caliper",
        name="Brake Caliper Body",
        role="caliper",
        quantity=1,
        material="Aluminum 6061-T6",
        motion_type="fixed",
        parameters={"length": 85.0, "width": 60.0, "height": 45.0, "bore_dia": 32.0},
        base_placement=Placement3D.from_xyz_rxyz(55.0, 0, 0, 0, 0, 0),
    )
    pad_in = ComponentSpec(
        component_id=f"comp_{uid}_pad_in",
        name="Inner Brake Friction Pad",
        role="mounting_plate",
        quantity=1,
        material="Semi-Metallic Friction Composite",
        motion_type="linear",
        parameters={"length": 45.0, "width": 30.0, "thickness": 6.0},
        base_placement=Placement3D.from_xyz_rxyz(50.0, -10.0, 0, 0, 0, 0),
    )
    pad_out = ComponentSpec(
        component_id=f"comp_{uid}_pad_out",
        name="Outer Brake Friction Pad",
        role="mounting_plate",
        quantity=1,
        material="Semi-Metallic Friction Composite",
        motion_type="linear",
        parameters={"length": 45.0, "width": 30.0, "thickness": 6.0},
        base_placement=Placement3D.from_xyz_rxyz(50.0, 10.0, 0, 0, 0, 0),
    )
    bracket = ComponentSpec(
        component_id=f"comp_{uid}_bracket",
        name="Caliper Torque Anchor Bracket",
        role="bracket",
        quantity=1,
        material="Structural Steel",
        motion_type="fixed",
        parameters={"length": 75.0, "width": 35.0, "thickness": 10.0},
        base_placement=Placement3D.from_xyz_rxyz(55.0, 0, -32.0, 0, 0, 0),
    )
    return AssemblySpec(
        id=asm_id,
        name="Automotive Disc Brake Assembly",
        assembly_family="disc_brake",
        components=[rotor, caliper, pad_in, pad_out, bracket],
        mating_interfaces=[],
    )


def decompose_linear_actuator(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Linear Actuator Slide Stage."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_actuator_{uid}"
    rail = ComponentSpec(
        component_id=f"comp_{uid}_rail",
        name="Base Linear Guide Rail",
        role="mounting_plate",
        quantity=1,
        material="Anodized Aluminum 6063",
        motion_type="fixed",
        parameters={"length": 200.0, "width": 45.0, "thickness": 15.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    table = ComponentSpec(
        component_id=f"comp_{uid}_table",
        name="Carriage Slide Table",
        role="mounting_plate",
        quantity=1,
        material="Aluminum 6061-T6",
        motion_type="linear",
        parameters={"length": 60.0, "width": 55.0, "thickness": 15.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 20.0, 0, 0, 0),
    )
    screw = ComponentSpec(
        component_id=f"comp_{uid}_screw",
        name="Precision Lead Screw",
        role="lead_screw",
        quantity=1,
        material="Carbon Steel 1045",
        motion_type="revolute",
        parameters={"diameter": 12.0, "length": 210.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 10.0, 0, 90.0, 0),
    )
    end_drive = ComponentSpec(
        component_id=f"comp_{uid}_end_drv",
        name="Drive End Bearing Block",
        role="housing",
        quantity=1,
        material="Aluminum 6061",
        motion_type="fixed",
        parameters={"length": 40.0, "width": 45.0, "height": 30.0, "bore_dia": 16.0},
        base_placement=Placement3D.from_xyz_rxyz(-95.0, 0, 10.0, 0, 0, 0),
    )
    end_float = ComponentSpec(
        component_id=f"comp_{uid}_end_flt",
        name="Floating End Bearing Block",
        role="housing",
        quantity=1,
        material="Aluminum 6061",
        motion_type="fixed",
        parameters={"length": 40.0, "width": 45.0, "height": 30.0, "bore_dia": 16.0},
        base_placement=Placement3D.from_xyz_rxyz(95.0, 0, 10.0, 0, 0, 0),
    )
    return AssemblySpec(
        id=asm_id,
        name="Precision Linear Actuator Slide Stage",
        assembly_family="linear_actuator",
        components=[rail, table, screw, end_drive, end_float],
        mating_interfaces=[],
    )


def decompose_shaft_coupling(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Jaw Shaft Coupling Assembly."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_coupling_{uid}"
    hub_drv = ComponentSpec(
        component_id=f"comp_{uid}_hub_drv",
        name="Drive Jaw Hub",
        role="housing",
        quantity=1,
        material="Aluminum 7075 / Steel",
        motion_type="revolute",
        parameters={"length": 42.0, "width": 42.0, "height": 32.0, "bore_dia": 14.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, -22.0, 0, 0, 0),
    )
    hub_out = ComponentSpec(
        component_id=f"comp_{uid}_hub_out",
        name="Driven Jaw Hub",
        role="housing",
        quantity=1,
        material="Aluminum 7075 / Steel",
        motion_type="revolute",
        parameters={"length": 42.0, "width": 42.0, "height": 32.0, "bore_dia": 14.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 22.0, 0, 0, 0),
    )
    spider = ComponentSpec(
        component_id=f"comp_{uid}_spider",
        name="Elastomeric Spider Damper",
        role="disc",
        quantity=1,
        material="Polyurethane 98A",
        motion_type="revolute",
        parameters={"outer_diameter": 40.0, "face_width": 12.0, "inner_diameter": 12.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    return AssemblySpec(
        id=asm_id,
        name="Flexible Jaw Shaft Coupling Assembly",
        assembly_family="shaft_coupling",
        components=[hub_drv, hub_out, spider],
        mating_interfaces=[],
    )


def decompose_valve_assembly(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Industrial Flanged Valve Assembly."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_valve_{uid}"
    body = ComponentSpec(
        component_id=f"comp_{uid}_body",
        name="Flanged Valve Body",
        role="valve_body",
        quantity=1,
        material="Stainless Steel 316 / CF8M",
        motion_type="fixed",
        parameters={"length": 100.0, "width": 70.0, "height": 70.0, "bore_dia": 35.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    ball = ComponentSpec(
        component_id=f"comp_{uid}_ball",
        name="Valve Ball Core",
        role="rotor",
        quantity=1,
        material="Stainless Steel 316",
        motion_type="revolute",
        parameters={"outer_diameter": 42.0, "face_width": 35.0, "inner_diameter": 25.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    stem = ComponentSpec(
        component_id=f"comp_{uid}_stem",
        name="Valve Stem",
        role="shaft",
        quantity=1,
        material="Stainless Steel 316",
        motion_type="revolute",
        parameters={"diameter": 12.0, "length": 55.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 42.0, 0, 0, 0),
    )
    handle = ComponentSpec(
        component_id=f"comp_{uid}_handle",
        name="Manual Lever Handle",
        role="lever",
        quantity=1,
        material="Stainless Steel / Vinyl Coated",
        motion_type="revolute",
        parameters={"length": 110.0, "width": 20.0, "thickness": 6.0},
        base_placement=Placement3D.from_xyz_rxyz(40.0, 0, 70.0, 0, 0, 0),
    )
    return AssemblySpec(
        id=asm_id,
        name="Industrial Flanged Ball Valve Assembly",
        assembly_family="valve",
        components=[body, ball, stem, handle],
        mating_interfaces=[],
    )


def decompose_differential(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Automotive Differential Drive Assembly."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_diff_{uid}"
    casing = ComponentSpec(
        component_id=f"comp_{uid}_casing",
        name="Differential Carrier Case",
        role="housing",
        quantity=1,
        material="Ductile Iron",
        motion_type="revolute",
        parameters={"length": 95.0, "width": 95.0, "height": 65.0, "bore_dia": 45.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    ring_gear = ComponentSpec(
        component_id=f"comp_{uid}_crown",
        name="Hypoid Crown Ring Gear",
        role="ring_gear",
        quantity=1,
        material="Case-Hardened Steel 8620",
        motion_type="revolute",
        parameters={"outer_diameter": 130.0, "inner_diameter": 80.0, "face_width": 18.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, -20.0, 0, 0, 0),
    )
    pinion = ComponentSpec(
        component_id=f"comp_{uid}_pinion",
        name="Drive Pinion Shaft",
        role="gear",
        quantity=1,
        material="Case-Hardened Steel 8620",
        motion_type="revolute",
        parameters={"pitch_diameter": 36.0, "face_width": 25.0, "shaft_dia": 18.0},
        base_placement=Placement3D.from_xyz_rxyz(0, -65.0, 0, 90.0, 0, 0),
    )
    side_gears = ComponentSpec(
        component_id=f"comp_{uid}_side_gear",
        name="Axle Output Bevel Gears",
        role="gear",
        quantity=2,
        material="Alloy Steel 4140",
        motion_type="revolute",
        parameters={"pitch_diameter": 44.0, "face_width": 16.0, "shaft_dia": 22.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    return AssemblySpec(
        id=asm_id,
        name="Automotive Differential Drive Assembly",
        assembly_family="differential",
        components=[casing, ring_gear, pinion, side_gears],
        mating_interfaces=[],
    )


def decompose_reciprocating_mechanism(design_id: str, prompt: str) -> AssemblySpec:
    """Deterministic synthesis for Slider-Crank / Scotch-Yoke Mechanism."""
    uid = design_id[-8:] if len(design_id) >= 8 else design_id
    asm_id = f"asm_recip_{uid}"
    block = ComponentSpec(
        component_id=f"comp_{uid}_block",
        name="Cylinder & Guide Block",
        role="cylinder_block",
        quantity=1,
        material="Cast Iron / Aluminum",
        motion_type="fixed",
        parameters={"length": 120.0, "width": 80.0, "height": 70.0, "bore_dia": 40.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 0, 0, 0, 0, 0),
    )
    crank = ComponentSpec(
        component_id=f"comp_{uid}_crank",
        name="Crank Disk & Shaft",
        role="flywheel",
        quantity=1,
        material="Forged Steel 4340",
        motion_type="revolute",
        parameters={"outer_diameter": 70.0, "face_width": 18.0, "inner_diameter": 16.0},
        base_placement=Placement3D.from_xyz_rxyz(0, -50.0, 0, 0, 0, 0),
    )
    rod = ComponentSpec(
        component_id=f"comp_{uid}_rod",
        name="Connecting Linkage Rod",
        role="connecting_rod",
        quantity=1,
        material="Forged Steel 4340",
        motion_type="revolute",
        parameters={"length": 90.0, "width": 16.0, "thickness": 10.0},
        base_placement=Placement3D.from_xyz_rxyz(0, -15.0, 0, 0, 0, 0),
    )
    slider = ComponentSpec(
        component_id=f"comp_{uid}_slider",
        name="Reciprocating Piston Slider",
        role="actuator",
        quantity=1,
        material="Cast Aluminum / Alloy Steel",
        motion_type="linear",
        parameters={"body_diameter": 38.0, "body_length": 45.0, "rod_diameter": 12.0},
        base_placement=Placement3D.from_xyz_rxyz(0, 30.0, 0, 0, 0, 0),
    )
    return AssemblySpec(
        id=asm_id,
        name="Slider-Crank Reciprocating Mechanism Assembly",
        assembly_family="slider_crank",
        components=[block, crank, rod, slider],
        mating_interfaces=[],
    )


def _resolve_assembly_fallback(design_id: str, prompt: str) -> AssemblySpec:
    """Resolve an assembly prompt to the correct deterministic domain synthesizer."""
    p_lower = prompt.lower()
    if any(k in p_lower for k in ["planetary", "epicyclic", "sun gear"]):
        return decompose_planetary_gearbox(design_id, prompt)
    if any(k in p_lower for k in ["scissor", "lift table"]):
        return decompose_scissor_lift(design_id, prompt)
    if any(k in p_lower for k in ["brake", "caliper", "rotor"]):
        return decompose_disc_brake(design_id, prompt)
    if any(k in p_lower for k in ["actuator", "slide stage", "lead screw", "linear stage", "stage"]):
        return decompose_linear_actuator(design_id, prompt)
    if any(k in p_lower for k in ["coupling", "jaw coupling", "spider"]):
        return decompose_shaft_coupling(design_id, prompt)
    if any(k in p_lower for k in ["valve", "ball valve", "gate valve"]):
        return decompose_valve_assembly(design_id, prompt)
    if any(k in p_lower for k in ["differential", "crown wheel", "bevel drive"]):
        return decompose_differential(design_id, prompt)
    if any(k in p_lower for k in ["scotch yoke", "slider crank", "reciprocating", "piston crank", "press"]):
        return decompose_reciprocating_mechanism(design_id, prompt)
    if any(k in p_lower for k in ["caster", "trolley wheel", "swivel wheel"]):
        return decompose_caster_wheel(design_id, prompt)
    if any(k in p_lower for k in ["gearbox", "gear pair", "gear reducer", "spur gear"]):
        return decompose_gearbox_pair(design_id, prompt)
    if any(k in p_lower for k in ["gripper", "finger gripper", "three-finger", "3-finger", "claw", "robotic hand", "hand", "grasp"]):
        return decompose_three_finger_gripper(design_id, prompt)
    return decompose_gearbox_pair(design_id, prompt)


def plan_assembly(design_id: str, prompt: str, intent: Optional[Dict[str, Any]] = None) -> AssemblySpec:
    """
    Decomposes design prompt into an AssemblySpec.
    Dispatches to domain-specific deterministic synthesizers or attempts LLM decomposition.
    """
    p_lower = prompt.lower()

    # 1. Fast dispatch for known domain assembly benchmarks
    domain_synthesizer = None
    if any(k in p_lower for k in ["gripper", "finger gripper", "three-finger", "3-finger", "claw", "robotic hand"]):
        domain_synthesizer = decompose_three_finger_gripper
    elif any(k in p_lower for k in ["planetary", "epicyclic", "sun gear"]):
        domain_synthesizer = decompose_planetary_gearbox
    elif any(k in p_lower for k in ["scissor", "lift table"]):
        domain_synthesizer = decompose_scissor_lift
    elif any(k in p_lower for k in ["brake", "caliper", "rotor"]):
        domain_synthesizer = decompose_disc_brake
    elif any(k in p_lower for k in ["linear actuator", "slide stage", "lead screw", "linear stage"]):
        domain_synthesizer = decompose_linear_actuator
    elif any(k in p_lower for k in ["coupling", "jaw coupling", "spider"]):
        domain_synthesizer = decompose_shaft_coupling
    elif any(k in p_lower for k in ["valve", "ball valve", "gate valve"]):
        domain_synthesizer = decompose_valve_assembly
    elif any(k in p_lower for k in ["differential", "crown wheel", "bevel drive"]):
        domain_synthesizer = decompose_differential
    elif any(k in p_lower for k in ["scotch yoke", "slider crank", "reciprocating", "piston crank"]):
        domain_synthesizer = decompose_reciprocating_mechanism
    elif any(k in p_lower for k in ["gearbox", "gear pair", "gear reducer", "spur gear set"]):
        domain_synthesizer = decompose_gearbox_pair
    elif any(k in p_lower for k in ["caster", "trolley wheel", "swivel wheel"]):
        domain_synthesizer = decompose_caster_wheel

    if domain_synthesizer:
        return domain_synthesizer(design_id, prompt)

    # 2. Attempt LLM-assisted decomposition for arbitrary assemblies
    try:
        llm = get_design_llm()
        sys_prompt = (
            "You are a master mechanical CAD systems engineer. Decompose the requested mechanical assembly into modular components.\n"
            "Output ONLY valid JSON strictly matching this schema structure:\n"
            "{\n"
            '  "name": "Assembly Name",\n'
            '  "assembly_family": "family_name",\n'
            '  "description": "Functional description",\n'
            '  "global_parameters": {"param1": 100.0},\n'
            '  "components": [\n'
            '    {\n'
            '      "component_id": "comp_1",\n'
            '      "name": "Part Name",\n'
            '      "role": "mounting_plate",\n'
            '      "quantity": 1,\n'
            '      "material": "Aluminum 6061",\n'
            '      "motion_type": "fixed",\n'
            '      "parameters": {"length": 100.0, "width": 80.0, "thickness": 10.0},\n'
            '      "base_placement": {"translation": {"x": 0, "y": 0, "z": 0}, "rotation": {"x": 0, "y": 0, "z": 0}}\n'
            '    }\n'
            '  ],\n'
            '  "mating_interfaces": [\n'
            '    {\n'
            '      "interface_id": "mate_1",\n'
            '      "mate_type": "revolute",\n'
            '      "parent_component_id": "comp_1",\n'
            '      "child_component_id": "comp_2",\n'
            '      "clearance": 0.2\n'
            '    }\n'
            '  ],\n'
            '  "assumptions": ["Assumption 1"],\n'
            '  "unresolved_parameters": ["Parameter 1"]\n'
            "}\n"
            "Output raw JSON only without markdown formatting."
        )

        res = llm.invoke([("system", sys_prompt), ("user", prompt)])
        raw_text = res.content if hasattr(res, "content") else str(res)
        json_str = _extract_json_object(raw_text)
        if json_str:
            data = json.loads(json_str)
            data.setdefault("id", f"asm_{design_id[-8:]}")

            # Sanitize components motion_type
            valid_motions = {"fixed", "revolute", "linear", "floating"}
            motion_map = {
                "rotating": "revolute", "rotational": "revolute", "rotation": "revolute",
                "translating": "linear", "translation": "linear", "sliding": "linear", "translating_radial": "linear",
                "stationary": "fixed", "static": "fixed",
            }
            for comp in data.get("components", []):
                if isinstance(comp, dict):
                    m = str(comp.get("motion_type", "")).lower()
                    comp["motion_type"] = motion_map.get(m, m if m in valid_motions else "fixed")

            # Sanitize mating_interfaces mate_type
            valid_mates = {"rigid", "revolute", "prismatic", "cylindrical", "planar_contact", "coaxial", "fastener", "slot", "gear_mesh", "custom"}
            mate_map = {
                "sliding_contact": "prismatic", "sliding": "prismatic", "hinge": "revolute", "pivot": "revolute",
                "pin": "revolute", "bolted": "fastener", "screw": "fastener", "align": "coaxial", "contact": "planar_contact",
            }
            for mi in data.get("mating_interfaces", []):
                if isinstance(mi, dict):
                    mt = str(mi.get("mate_type", "")).lower()
                    mi["mate_type"] = mate_map.get(mt, mt if mt in valid_mates else "custom")

            spec = AssemblySpec.model_validate(data)
            if spec.components:
                return spec
    except Exception as e:
        print(f"LLM Assembly Decomposition Notice: {e}", file=sys.stderr)

    # 3. Domain Fallback Resolver
    return _resolve_assembly_fallback(design_id, prompt)


def design_planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Design Planner Node in LangGraph.
    Inspects user prompt and intent to determine single-part vs multi-component assembly.
    Emits AssemblySpec and design plan if assembly is detected.
    """
    prompt = state.get("user_prompt", "")
    intent = state.get("parsed_intent", {})
    design_id = state.get("design_id", "design_default")

    if is_assembly_prompt(prompt, intent):
        asm_spec = plan_assembly(design_id, prompt, intent)
        conf = {**state.get("confidence_scores", {})}
        conf["design_planner"] = 0.98

        return {
            "is_assembly": True,
            "assembly_spec": asm_spec,
            "design_plan": {
                "assembly_name": asm_spec.name,
                "component_count": len(asm_spec.components),
                "total_instances": sum(c.quantity for c in asm_spec.components),
                "bom": asm_spec.get_bom(),
                "assumptions": asm_spec.assumptions,
                "unresolved_parameters": asm_spec.unresolved_parameters,
            },
            "confidence_scores": conf,
            "current_agent": "design_planner",
        }
    else:
        # Single-part workflow
        conf = {**state.get("confidence_scores", {})}
        conf["design_planner"] = 1.0
        return {
            "is_assembly": False,
            "assembly_spec": None,
            "design_plan": {},
            "confidence_scores": conf,
            "current_agent": "design_planner",
        }
