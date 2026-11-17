"""
Assembly Parametric Propagation Engine.
Propagates global and interface parameter changes across components,
recomputing dependent placements, dimensions, clearances, and CADIR definitions.
"""
from typing import Dict, Any, List, Optional
import math
import copy

from cad.assembly.schema import AssemblySpec, ComponentSpec, Placement3D
from cad.assembly.component_generator import generate_component_cadir


def propagate_assembly_parameters(
    asm_spec: AssemblySpec,
    updated_params: Dict[str, float],
) -> AssemblySpec:
    """
    Applies updated parameter values to an AssemblySpec and propagates
    dimensional and spatial dependencies throughout all components.
    """
    updated_spec = copy.deepcopy(asm_spec)

    # 1. Update Global Parameters
    updated_spec.global_parameters.update(updated_params)
    globals_ = updated_spec.global_parameters

    family = (updated_spec.assembly_family or "").lower()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. THREE-FINGER GRIPPER PARAMETER PROPAGATION
    # ─────────────────────────────────────────────────────────────────────────
    if family == "gripper" or "finger" in updated_spec.name.lower():
        # Extracted or updated parameters
        stroke = globals_.get("stroke", 25.0)
        finger_span = globals_.get("finger_span", 150.0)
        mount_dia = globals_.get("mounting_diameter", 120.0)
        finger_mount_rad = mount_dia * 0.375  # proportional spacing

        # Pin diameter propagation
        pin_dia = globals_.get("pin_diameter", 8.0)

        for comp in updated_spec.components:
            role = comp.role.lower()

            if role == "mounting_plate":
                comp.parameters["diameter"] = mount_dia
                comp.parameters["mount_radius"] = finger_mount_rad
                comp.parameters["pin_hole_dia"] = pin_dia
                comp.cadir_document = generate_component_cadir(comp, updated_spec)

            elif role == "finger":
                comp.parameters["length"] = globals_.get("finger_length", finger_span * 0.5)
                comp.parameters["pivot_hole_dia"] = pin_dia
                comp.cadir_document = generate_component_cadir(comp, updated_spec)

                # Recompute polar instance placements
                new_placements = []
                for angle_deg in [0.0, 120.0, 240.0]:
                    rad = math.radians(angle_deg)
                    fx = round(finger_mount_rad * math.cos(rad), 2)
                    fy = round(finger_mount_rad * math.sin(rad), 2)
                    new_placements.append(
                        Placement3D.from_xyz_rxyz(fx, fy, 23.5, rx=0, ry=0, rz=round(angle_deg, 2))
                    )
                comp.instance_placements = new_placements

            elif role == "pivot_pin":
                comp.parameters["diameter"] = pin_dia - 0.05
                comp.cadir_document = generate_component_cadir(comp, updated_spec)
                new_pin_placements = []
                for angle_deg in [0.0, 120.0, 240.0]:
                    rad = math.radians(angle_deg)
                    fx = round(finger_mount_rad * math.cos(rad), 2)
                    fy = round(finger_mount_rad * math.sin(rad), 2)
                    new_pin_placements.append(
                        Placement3D.from_xyz_rxyz(fx, fy, 11.0, rx=0, ry=0, rz=round(angle_deg, 2))
                    )
                comp.instance_placements = new_pin_placements

            elif role == "linkage":
                comp.cadir_document = generate_component_cadir(comp, updated_spec)
                new_link_placements = []
                for angle_deg in [0.0, 120.0, 240.0]:
                    rad = math.radians(angle_deg)
                    lx = round((finger_mount_rad * 0.55) * math.cos(rad), 2)
                    ly = round((finger_mount_rad * 0.55) * math.sin(rad), 2)
                    new_link_placements.append(
                        Placement3D.from_xyz_rxyz(lx, ly, 35.0, rx=0, ry=15.0, rz=round(angle_deg, 2))
                    )
                comp.instance_placements = new_link_placements

            elif role == "actuator":
                comp.parameters["stroke"] = stroke
                comp.cadir_document = generate_component_cadir(comp, updated_spec)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. GEARBOX PARAMETER PROPAGATION
    # ─────────────────────────────────────────────────────────────────────────
    elif family == "gearbox":
        cd = globals_.get("center_distance", 60.0)
        for comp in updated_spec.components:
            role = comp.role.lower()
            if role == "housing":
                comp.parameters["center_distance"] = cd
                comp.cadir_document = generate_component_cadir(comp, updated_spec)
            elif "pinion" in comp.name.lower():
                comp.base_placement = Placement3D.from_xyz_rxyz(-cd / 2.0, 0, 15.0, 0, 0, 0)
                comp.instance_placements = [comp.base_placement]
            elif "gear" in comp.name.lower():
                comp.base_placement = Placement3D.from_xyz_rxyz(cd / 2.0, 0, 15.0, 0, 0, 0)
                comp.instance_placements = [comp.base_placement]

    # ─────────────────────────────────────────────────────────────────────────
    # 3. GENERIC RE-GENERATION
    # ─────────────────────────────────────────────────────────────────────────
    else:
        for comp in updated_spec.components:
            for k, v in updated_params.items():
                if k in comp.parameters:
                    comp.parameters[k] = v
            comp.cadir_document = generate_component_cadir(comp, updated_spec)

    return updated_spec
