"""
Assembly Component CADIR Generator.
Generates fully parametric CADIR documents for individual components in mechanical assemblies.
Ensures topological soundness, explicit dependencies, and engineering dimensional accuracy.
"""
from typing import Dict, Any, List, Optional
import math
import uuid

from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    CADIRSketchProfile,
    CADIRPlane,
    CADIRCircle,
    CADIRRectangle,
    Point3D,
    Vector3D,
)
from cad.cadir.validator import validate_cadir_document
from cad.assembly.schema import ComponentSpec, AssemblySpec


def generate_component_cadir(
    comp: ComponentSpec,
    asm_spec: Optional[AssemblySpec] = None,
) -> CADIRDocument:
    """
    Synthesizes a valid parametric CADIRDocument for a component specification.
    Tailors feature tree based on component role, parameters, and interfaces.
    """
    role = comp.role.lower()
    params = comp.parameters
    cid = comp.component_id
    uid = cid[-8:].replace("-", "_")

    doc = CADIRDocument(
        id=f"doc_{cid}",
        name=comp.name,
        component_family=role,
        difficulty="L2",
        material=comp.material,
        units="mm",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 1. MOUNTING PLATE
    # ─────────────────────────────────────────────────────────────────────────
    if role in ("mounting_plate", "base_plate", "clevis_plate", "top_plate"):
        is_gripper = (asm_spec and asm_spec.assembly_family == "gripper") or "clevis" in comp.name.lower()
        if is_gripper:
            dia = params.get("diameter", 120.0)
            thickness = params.get("thickness", 12.0)
            center_bore = params.get("center_bore", 32.0)
            mount_rad = params.get("mount_radius", 45.0)
            lug_h = params.get("lug_height", 18.0)
            pin_dia = params.get("pin_hole_dia", 8.0)

            # Base circular disk
            f1 = CADIRFeature(
                id=f"f_{uid}_base",
                name="Plate Base Disk",
                feature_type="cylinder",
                radius=dia / 2.0,
                height=thickness,
                operation="new_body",
                dependencies=[],
            )
            # Center bore for actuator
            f2 = CADIRFeature(
                id=f"f_{uid}_center_bore",
                name="Actuator Center Bore",
                feature_type="hole",
                diameter=center_bore,
                depth=thickness * 2.0,
                position=Point3D(x=0.0, y=0.0, z=0.0),
                operation="cut",
                dependencies=[f1.id],
            )
            prev_dep = f2.id
            doc.features.extend([f1, f2])

            # 3 Clevis Lug Blocks at 120 deg
            for i, angle_deg in enumerate([0.0, 120.0, 240.0]):
                rad = math.radians(angle_deg)
                lx = round(mount_rad * math.cos(rad), 2)
                ly = round(mount_rad * math.sin(rad), 2)
                f_lug = CADIRFeature(
                    id=f"f_{uid}_lug_{i+1}",
                    name=f"Clevis Mounting Lug {i+1}",
                    feature_type="box",
                    length=22.0,
                    width=24.0,
                    height=lug_h,
                    position=Point3D(x=lx, y=ly, z=thickness + lug_h / 2.0),
                    operation="join",
                    dependencies=[prev_dep],
                )
                doc.features.append(f_lug)

                # Clevis gap to house the articulated finger
                f_slot = CADIRFeature(
                    id=f"f_{uid}_clevis_slot_{i+1}",
                    name=f"Clevis Slot {i+1}",
                    feature_type="pocket",
                    length=26.0,
                    width=11.5,
                    height=lug_h * 1.2,
                    position=Point3D(x=lx, y=ly, z=thickness + lug_h * 0.6),
                    operation="cut",
                    dependencies=[f_lug.id],
                )
                doc.features.append(f_slot)

                # Clevis pin through hole across both ears
                f_hole = CADIRFeature(
                    id=f"f_{uid}_pin_hole_{i+1}",
                    name=f"Lug Pin Hole {i+1}",
                    feature_type="hole",
                    diameter=pin_dia,
                    depth=30.0,
                    position=Point3D(x=lx, y=ly, z=thickness + lug_h * 0.65),
                    operation="cut",
                    dependencies=[f_slot.id],
                )
                doc.features.append(f_hole)
                prev_dep = f_hole.id
        else:
            # Clean standard rectangular or circular mounting plate
            if "length" in params and "width" in params:
                l = params.get("length", 120.0)
                w = params.get("width", 80.0)
                t = params.get("thickness", 12.0)
                f1 = CADIRFeature(
                    id=f"f_{uid}_base",
                    name=f"{comp.name} Plate",
                    feature_type="box",
                    length=l,
                    width=w,
                    height=t,
                    operation="new_body",
                    dependencies=[],
                )
                doc.features.append(f1)
                bore = params.get("center_bore", params.get("bore_dia", None))
                if bore:
                    f2 = CADIRFeature(
                        id=f"f_{uid}_bore",
                        name="Center Bore",
                        feature_type="hole",
                        diameter=bore,
                        depth=t * 2.0,
                        position=Point3D(x=0.0, y=0.0, z=0.0),
                        operation="cut",
                        dependencies=[f1.id],
                    )
                    doc.features.append(f2)
            else:
                dia = params.get("diameter", 100.0)
                t = params.get("thickness", 10.0)
                f1 = CADIRFeature(
                    id=f"f_{uid}_base",
                    name=f"{comp.name} Disk",
                    feature_type="cylinder",
                    radius=dia / 2.0,
                    height=t,
                    operation="new_body",
                    dependencies=[],
                )
                doc.features.append(f1)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. ARTICULATED FINGER
    # ─────────────────────────────────────────────────────────────────────────
    elif role in ("finger", "claw", "jaw"):
        length = params.get("length", 75.0)
        width = params.get("width", 16.0)
        thickness = params.get("thickness", 10.0)
        pivot_hole_dia = params.get("pivot_hole_dia", 8.0)
        link_hole_dia = params.get("link_hole_dia", 5.0)

        # Main finger beam
        f1 = CADIRFeature(
            id=f"f_{uid}_body",
            name="Finger Beam Body",
            feature_type="box",
            length=length,
            width=width,
            height=thickness,
            position=Point3D(x=length / 2.0 - 10.0, y=0.0, z=thickness / 2.0),
            operation="new_body",
            dependencies=[],
        )
        # Hinge pivot hole
        f2 = CADIRFeature(
            id=f"f_{uid}_pivot_hole",
            name="Main Hinge Pivot Hole",
            feature_type="hole",
            diameter=pivot_hole_dia,
            depth=thickness * 2.0,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f1.id],
        )
        # Linkage drive hole
        f3 = CADIRFeature(
            id=f"f_{uid}_link_hole",
            name="Linkage Drive Hole",
            feature_type="hole",
            diameter=link_hole_dia,
            depth=thickness * 2.0,
            position=Point3D(x=22.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f2.id],
        )
        # Finger tip taper pocket
        f4 = CADIRFeature(
            id=f"f_{uid}_tip_taper",
            name="Finger Tip Taper Pocket",
            feature_type="pocket",
            length=length * 0.4,
            width=width * 0.5,
            height=thickness * 0.6,
            position=Point3D(x=length - 15.0, y=0.0, z=thickness * 0.7),
            operation="cut",
            dependencies=[f3.id],
        )
        doc.features.extend([f1, f2, f3, f4])

    # ─────────────────────────────────────────────────────────────────────────
    # 3. PIVOT PIN
    # ─────────────────────────────────────────────────────────────────────────
    elif role in ("pivot_pin", "pin", "dowel"):
        dia = params.get("diameter", 7.95)
        length = params.get("length", 26.0)
        head_dia = params.get("head_diameter", 12.0)
        head_t = params.get("head_thickness", 3.0)

        f1 = CADIRFeature(
            id=f"f_{uid}_shaft",
            name="Pin Main Shaft",
            feature_type="cylinder",
            radius=dia / 2.0,
            height=length,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_head",
            name="Pin Retaining Head",
            feature_type="cylinder",
            radius=head_dia / 2.0,
            height=head_t,
            position=Point3D(x=0.0, y=0.0, z=length),
            operation="join",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_chamfer",
            name="Lead-in Chamfer",
            feature_type="chamfer",
            distance=0.8,
            edge_selector="bottom",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ─────────────────────────────────────────────────────────────────────────
    # 4. LINKAGE
    # ─────────────────────────────────────────────────────────────────────────
    elif role in ("linkage", "link", "drive_arm"):
        length = params.get("length", 42.0)
        width = params.get("width", 12.0)
        thickness = params.get("thickness", 5.0)
        h1 = params.get("hole1_dia", 5.0)
        h2 = params.get("hole2_dia", 5.0)

        f1 = CADIRFeature(
            id=f"f_{uid}_arm",
            name="Link Arm Solid",
            feature_type="box",
            length=length,
            width=width,
            height=thickness,
            position=Point3D(x=length / 2.0, y=0.0, z=thickness / 2.0),
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_hole_in",
            name="Drive End Hole",
            feature_type="hole",
            diameter=h1,
            depth=thickness * 2.0,
            position=Point3D(x=6.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_hole_out",
            name="Output End Hole",
            feature_type="hole",
            diameter=h2,
            depth=thickness * 2.0,
            position=Point3D(x=length - 6.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ─────────────────────────────────────────────────────────────────────────
    # 5. LINEAR ACTUATOR & CROSSHEAD
    # ─────────────────────────────────────────────────────────────────────────
    elif role in ("actuator", "piston", "slider"):
        body_dia = params.get("body_diameter", 30.0)
        body_len = params.get("body_length", 65.0)
        rod_dia = params.get("rod_diameter", 12.0)
        ch_dia = params.get("crosshead_diameter", 28.0)
        ch_t = params.get("crosshead_thickness", 10.0)

        f1 = CADIRFeature(
            id=f"f_{uid}_body",
            name="Actuator Cylinder Body",
            feature_type="cylinder",
            radius=body_dia / 2.0,
            height=body_len,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_rod",
            name="Piston Extension Rod",
            feature_type="cylinder",
            radius=rod_dia / 2.0,
            height=30.0,
            position=Point3D(x=0.0, y=0.0, z=body_len),
            operation="join",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_crosshead",
            name="Linkage Crosshead Hub",
            feature_type="cylinder",
            radius=ch_dia / 2.0,
            height=ch_t,
            position=Point3D(x=0.0, y=0.0, z=body_len + 30.0),
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ─────────────────────────────────────────────────────────────────────────
    # 6. GEAR
    # ─────────────────────────────────────────────────────────────────────────
    elif role in ("gear", "pinion", "sprocket"):
        pd = params.get("pitch_diameter", 48.0)
        fw = params.get("face_width", 15.0)
        shaft_dia = params.get("shaft_dia", 14.0)

        f1 = CADIRFeature(
            id=f"f_{uid}_blank",
            name="Gear Blank Cylinder",
            feature_type="cylinder",
            radius=pd / 2.0,
            height=fw,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_bore",
            name="Shaft Bore Hole",
            feature_type="hole",
            diameter=shaft_dia,
            depth=fw * 2.0,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # ─────────────────────────────────────────────────────────────────────────
    # 7. SHAFT / SPINDLE / AXLE / LEAD SCREW
    # ─────────────────────────────────────────────────────────────────────────
    elif role in ("shaft", "axle", "spindle", "rotor_shaft", "lead_screw", "pin_shaft"):
        dia = params.get("diameter", params.get("shaft_dia", 16.0))
        length = params.get("length", params.get("shaft_len", 80.0))
        f1 = CADIRFeature(
            id=f"f_{uid}_shaft",
            name=f"{comp.name} Shaft",
            feature_type="cylinder",
            radius=dia / 2.0,
            height=length,
            operation="new_body",
            dependencies=[],
        )
        doc.features.append(f1)

    # ─────────────────────────────────────────────────────────────────────────
    # 8. DISC / ROTOR / BRAKE ROTOR / RING GEAR / ANNULUS
    # ─────────────────────────────────────────────────────────────────────────
    elif role in ("disc", "rotor", "brake_rotor", "wheel", "flywheel", "ring_gear", "annulus"):
        od = params.get("outer_diameter", params.get("diameter", 110.0))
        fw = params.get("face_width", params.get("thickness", params.get("width", 15.0)))
        bore = params.get("inner_diameter", params.get("bore_dia", od * 0.35))
        f1 = CADIRFeature(
            id=f"f_{uid}_disc",
            name=f"{comp.name} Solid",
            feature_type="cylinder",
            radius=od / 2.0,
            height=fw,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_bore",
            name=f"{comp.name} Bore",
            feature_type="hole",
            diameter=bore,
            depth=fw * 2.0,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # ─────────────────────────────────────────────────────────────────────────
    # 9. HOUSING / CASING / CALIPER / VALVE BODY
    # ─────────────────────────────────────────────────────────────────────────
    elif role in ("housing", "casing", "caliper", "body", "valve_body", "cylinder_block"):
        l = params.get("length", 90.0)
        w = params.get("width", 70.0)
        h = params.get("height", params.get("thickness", 40.0))
        bore = params.get("bore_dia", min(l, w) * 0.45)
        f1 = CADIRFeature(
            id=f"f_{uid}_body",
            name=f"{comp.name} Body",
            feature_type="box",
            length=l,
            width=w,
            height=h,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_bore",
            name=f"{comp.name} Cavity",
            feature_type="hole",
            diameter=bore,
            depth=h * 2.0,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # ─────────────────────────────────────────────────────────────────────────
    # 10. LEVER / ARM / HANDLE
    # ─────────────────────────────────────────────────────────────────────────
    elif role in ("lever", "arm", "handle", "crank", "connecting_rod"):
        l = params.get("length", 80.0)
        w = params.get("width", 16.0)
        t = params.get("thickness", 8.0)
        h1 = params.get("hole1_dia", 8.0)
        f1 = CADIRFeature(
            id=f"f_{uid}_arm",
            name=f"{comp.name} Arm",
            feature_type="box",
            length=l,
            width=w,
            height=t,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_pivot",
            name="Pivot Hole",
            feature_type="hole",
            diameter=h1,
            depth=t * 2.0,
            position=Point3D(x=-(l / 2.0 - 10.0), y=0.0, z=0.0),
            operation="cut",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # ─────────────────────────────────────────────────────────────────────────
    # 11. DEFAULT / GENERIC BRACKET / FASTENER
    # ─────────────────────────────────────────────────────────────────────────
    else:
        l = params.get("length", 50.0)
        w = params.get("width", 30.0)
        h = params.get("thickness", params.get("height", 10.0))
        f1 = CADIRFeature(
            id=f"f_{uid}_base",
            name=f"{comp.name} Base",
            feature_type="box",
            length=l,
            width=w,
            height=h,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_hole",
            name=f"{comp.name} Mounting Bore",
            feature_type="hole",
            diameter=min(l, w) * 0.3,
            depth=h * 2.0,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # Run CADIR semantic validation
    val = validate_cadir_document(doc)
    if not val.is_valid:
        print(f"Warning: synthesized component {comp.name} had validation errors: {val.errors}")

    return doc
