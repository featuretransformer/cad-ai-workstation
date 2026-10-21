"""
Deterministic CADIR -> build123d Interpreter.
Converts validated CADIR documents into clean, executable build123d Python code.
Ensures deterministic geometric construction without uncontrolled LLM arithmetic.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    CADIRSketchProfile,
    CADIRPlane,
    CADIRCircle,
    CADIRRectangle,
    CADIRLine,
    CADIRArc,
    CADIRPolygon,
    CADIRSlot,
    CADIRSketchPrimitive,
)
from cad.cadir.validator import validate_cadir_document


def _map_mode(operation: str) -> str:
    """Map CADIR boolean operation to build123d Mode."""
    op_map = {
        "new_body": "Mode.ADD",
        "join": "Mode.ADD",
        "cut": "Mode.SUBTRACT",
        "intersect": "Mode.INTERSECT",
        "union": "Mode.ADD",
    }
    return op_map.get(operation, "Mode.ADD")


def generate_build123d_code(doc: CADIRDocument) -> str:
    """
    Generate deterministic, standalone build123d Python code from a CADIR document.
    """
    # 1. Pre-validation
    val_result = validate_cadir_document(doc)
    if not val_result.is_valid:
        raise ValueError(
            f"Cannot interpret invalid CADIR document: {'; '.join(val_result.errors)}"
        )

    code_lines: List[str] = [
        '"""',
        f"Generated build123d code for CADIR Document: {doc.name} (ID: {doc.id})",
        f"Component Family: {doc.component_family or 'custom'}, Units: {doc.units}",
        '"""',
        "from build123d import *",
        "",
    ]

    # Global Parameters
    if doc.parameters:
        code_lines.append("# --- Parametric Variables ---")
        for k, v in doc.parameters.items():
            clean_k = k.replace(" ", "_")
            code_lines.append(f"{clean_k} = {v}")
        code_lines.append("")

    code_lines.append("with BuildPart() as p:")

    sketch_map: Dict[str, CADIRSketchProfile] = {s.id: s for s in doc.sketches}

    # Generate features in sequence
    for f in doc.features:
        if f.suppressed:
            continue

        f_type = f.feature_type
        mode = _map_mode(f.operation)
        code_lines.append(f"    # Feature: {f.name or f.id} ({f_type})")

        if f_type == "box":
            pos = f.center or f.position
            cx = pos.x if pos else 0.0
            cy = pos.y if pos else 0.0
            cz = pos.z if pos else 0.0
            l = f.length or 20.0
            w = f.width or 20.0
            h = f.height or 10.0
            if cx == 0 and cy == 0 and cz == 0:
                code_lines.append(
                    f"    Box(length={l}, width={w}, height={h}, mode={mode})"
                )
            else:
                code_lines.append(f"    with Locations(({cx}, {cy}, {cz})):")
                code_lines.append(
                    f"        Box(length={l}, width={w}, height={h}, mode={mode})"
                )

        elif f_type == "cylinder":
            pos = f.center or f.position
            cx = pos.x if pos else 0.0
            cy = pos.y if pos else 0.0
            cz = pos.z if pos else 0.0
            rad = f.radius or (f.diameter / 2.0 if f.diameter else 10.0)
            hgt = f.height or f.length or f.depth or 20.0
            if cx == 0 and cy == 0 and cz == 0:
                code_lines.append(
                    f"    Cylinder(radius={rad}, height={hgt}, mode={mode})"
                )
            else:
                code_lines.append(f"    with Locations(({cx}, {cy}, {cz})):")
                code_lines.append(
                    f"        Cylinder(radius={rad}, height={hgt}, mode={mode})"
                )

        elif f_type == "sphere":
            pos = f.center or f.position
            cx = pos.x if pos else 0.0
            cy = pos.y if pos else 0.0
            cz = pos.z if pos else 0.0
            rad = f.radius or (f.diameter / 2.0 if f.diameter else 10.0)
            if cx == 0 and cy == 0 and cz == 0:
                code_lines.append(f"    Sphere(radius={rad}, mode={mode})")
            else:
                code_lines.append(f"    with Locations(({cx}, {cy}, {cz})):")
                code_lines.append(f"        Sphere(radius={rad}, mode={mode})")

        elif f_type in ("regular_polygon", "hex_prism", "polygon_prism"):
            pos = f.center or f.position
            cx = pos.x if pos else 0.0
            cy = pos.y if pos else 0.0
            cz = pos.z if pos else 0.0
            sides = getattr(f, "side_count", 6) or 6
            rad = f.radius or (f.diameter / 2.0 if f.diameter else 10.0)
            hgt = f.height or f.length or 10.0
            if cx == 0 and cy == 0 and cz == 0:
                code_lines.append("    with BuildSketch():")
                code_lines.append(f"        RegularPolygon(radius={rad}, side_count={sides})")
                code_lines.append(f"    extrude(amount={hgt}, mode={mode})")
            else:
                code_lines.append(f"    with BuildSketch(Plane.XY.offset({cz})):")
                code_lines.append(f"        with Locations(({cx}, {cy})):")
                code_lines.append(f"            RegularPolygon(radius={rad}, side_count={sides})")
                code_lines.append(f"    extrude(amount={hgt}, mode={mode})")

        elif f_type == "groove":
            pos = f.position or f.center
            px = pos.x if pos else 0.0
            py = pos.y if pos else 0.0
            pz = pos.z if pos else 0.0
            r_out = getattr(f, "outer_radius", None) or (f.diameter / 2.0 if f.diameter else 15.0)
            w = getattr(f, "groove_width", None) or f.width or 2.0
            depth = f.depth or 1.0
            r_in = getattr(f, "inner_radius", None) or max(0.5, r_out - depth)
            code_lines.append("    with BuildPart(mode=Mode.SUBTRACT):")
            code_lines.append(f"        with Locations(({px}, {py}, {pz})):")
            code_lines.append(f"            Cylinder(radius={round(r_out + 1.0, 3)}, height={w})")
            code_lines.append(f"            Cylinder(radius={round(r_in, 3)}, height={round(w + 0.2, 3)}, mode=Mode.SUBTRACT)")

        elif f_type == "pocket":
            pos = f.position or f.center
            px = pos.x if pos else 0.0
            py = pos.y if pos else 0.0
            pz = pos.z if pos else 0.0
            dep = f.depth or f.height or 10.0
            if f.length and f.width:
                if px == 0 and py == 0 and pz == 0:
                    code_lines.append(
                        f"    Box(length={f.length}, width={f.width}, height={dep}, mode=Mode.SUBTRACT)"
                    )
                else:
                    code_lines.append(f"    with Locations(({px}, {py}, {pz})):")
                    code_lines.append(
                        f"        Box(length={f.length}, width={f.width}, height={dep}, mode=Mode.SUBTRACT)"
                    )
            elif f.radius or f.diameter:
                rad = f.radius or (f.diameter / 2.0 if f.diameter else 10.0)
                if px == 0 and py == 0 and pz == 0:
                    code_lines.append(
                        f"    Cylinder(radius={rad}, height={dep}, mode=Mode.SUBTRACT)"
                    )
                else:
                    code_lines.append(f"    with Locations(({px}, {py}, {pz})):")
                    code_lines.append(
                        f"        Cylinder(radius={rad}, height={dep}, mode=Mode.SUBTRACT)"
                    )

        elif f_type == "extrude":
            sketch = sketch_map.get(f.sketch_id)
            if sketch:
                _generate_sketch_code(sketch, code_lines, indent=4)
                both_flag = ", both=True" if f.symmetric else ""
                taper_flag = f", taper={f.taper_angle}" if f.taper_angle != 0.0 else ""
                code_lines.append(
                    f"    extrude(amount={f.distance}, mode={mode}{both_flag}{taper_flag})"
                )

        elif f_type == "revolve":
            sketch = sketch_map.get(f.sketch_id)
            if sketch:
                _generate_sketch_code(sketch, code_lines, indent=4)
                ang = f.angle if f.angle is not None else 360.0
                code_lines.append(f"    revolve(axis=Axis.Z, angle={ang}, mode={mode})")

        elif f_type in ("hole", "counterbore_hole", "countersink_hole"):
            pos = f.position or f.center
            px = pos.x if pos else 0.0
            py = pos.y if pos else 0.0
            pz = pos.z if pos else 0.0
            rad = f.radius or (f.diameter / 2.0 if f.diameter else 5.0)
            dep = f.depth or f.height

            is_cbore = (f_type == "counterbore_hole" or f.hole_type == "counterbore" or "counterbore" in (f.name or "").lower() or "cbore" in (f.name or "").lower())
            is_csink = (f_type == "countersink_hole" or f.hole_type == "countersink" or "countersink" in (f.name or "").lower() or "csink" in (f.name or "").lower())

            cb_r = f.cbore_diameter / 2.0 if f.cbore_diameter else None
            cb_dep = f.cbore_depth

            if is_cbore and (cb_r is None or cb_dep is None):
                import re
                from cad.standards.fasteners import lookup_counterbore
                match = re.search(r"\bM(\d+(?:\.\d+)?)\b", (f.name or "") + " " + (f.description or ""), re.IGNORECASE)
                std_info = lookup_counterbore(f"M{match.group(1)}") if match else None
                if not std_info and rad:
                    std_info = lookup_counterbore(f"M{int(round(rad * 2))}")
                if std_info:
                    rad = std_info["clearance_dia"] / 2.0
                    cb_r = std_info["cbore_dia"] / 2.0
                    cb_dep = std_info["cbore_depth"]

            code_lines.append(f"    with Locations(({px}, {py}, {pz})):")
            if is_cbore and cb_r and cb_dep:
                hole_dep = dep or 30.0
                code_lines.append(
                    f"        CounterBoreHole(radius={rad}, counter_bore_radius={cb_r}, counter_bore_depth={cb_dep}, depth={hole_dep})"
                )
            elif is_csink and (f.csink_diameter or is_csink):
                cs_r = f.csink_diameter / 2.0 if f.csink_diameter else rad * 1.8
                cs_ang = f.csink_angle or 90.0
                hole_dep = dep or 30.0
                code_lines.append(
                    f"        CounterSinkHole(radius={rad}, counter_sink_radius={cs_r}, counter_sink_angle={cs_ang}, depth={hole_dep})"
                )
            else:
                is_through = (
                    dep is None
                    or dep >= 15.0
                    or "through" in (f.name or "").lower()
                    or "bore" in (f.name or "").lower()
                    or "mounting" in (f.name or "").lower()
                )
                if is_through:
                    code_lines.append(f"        Hole(radius={rad}, depth=None)")
                else:
                    code_lines.append(f"        Hole(radius={rad}, depth={dep})")

        elif f_type == "fillet":
            rad = f.radius or 1.0
            selector = f.edge_selector or "all"
            code_lines.append("    try:")
            code_lines.append("        _edges = p.edges()")
            if selector == "top":
                code_lines.append("        _edges = _edges.sort_by(Axis.Z)[-4:]")
            elif selector == "bottom":
                code_lines.append("        _edges = _edges.sort_by(Axis.Z)[:4]")
            elif selector == "vertical":
                code_lines.append("        _edges = _edges.filter_by(Axis.Z)")
            code_lines.append(f"        if _edges:")
            code_lines.append(f"            fillet(_edges, radius={rad})")
            code_lines.append("    except Exception as _fe:")
            code_lines.append(f'        print(f"Fillet warning: {{_fe}}")')

        elif f_type == "chamfer":
            dist = f.distance or 1.0
            selector = f.edge_selector or "all"
            code_lines.append("    try:")
            code_lines.append("        _edges = p.edges()")
            if selector == "top":
                code_lines.append("        _edges = _edges.sort_by(Axis.Z)[-4:]")
            elif selector == "bottom":
                code_lines.append("        _edges = _edges.sort_by(Axis.Z)[:4] ")
            elif selector == "vertical":
                code_lines.append("        _edges = _edges.filter_by(Axis.Z)")
            code_lines.append(f"        if _edges:")
            code_lines.append(f"            chamfer(_edges, length={dist})")
            code_lines.append("    except Exception as _ce:")
            code_lines.append(f'        print(f"Chamfer warning: {{_ce}}")')

        elif f_type == "sweep":
            sketch = sketch_map.get(f.sketch_id)
            if sketch:
                _generate_sketch_code(sketch, code_lines, indent=4)
                if f.path_sketch_id and f.path_sketch_id in sketch_map:
                    path_sketch = sketch_map[f.path_sketch_id]
                    _generate_sketch_code(path_sketch, code_lines, indent=4)
                    code_lines.append(f"    sweep(mode={mode})")
                else:
                    amt = f.distance or f.length or 20.0
                    code_lines.append(f"    extrude(amount={amt}, mode={mode})")

        elif f_type == "loft":
            sketch_ids = f.section_sketch_ids or ([f.sketch_id] if f.sketch_id else [])
            for s_id in sketch_ids:
                sk = sketch_map.get(s_id)
                if sk:
                    _generate_sketch_code(sk, code_lines, indent=4)
            ruled_flag = ", ruled=True" if f.ruled else ""
            code_lines.append(f"    loft(mode={mode}{ruled_flag})")

        elif f_type == "shell":
            thick = f.thickness or 2.0
            openings = f.opening_faces or ["top"]
            code_lines.append("    try:")
            if "top" in openings:
                code_lines.append("        _openings = p.faces().sort_by(Axis.Z)[-1:]")
            elif "bottom" in openings:
                code_lines.append("        _openings = p.faces().sort_by(Axis.Z)[:1]")
            else:
                code_lines.append("        _openings = None")
            code_lines.append("        if _openings:")
            code_lines.append(f"            offset(openings=_openings, amount=-{thick})")
            code_lines.append("        else:")
            code_lines.append(f"            offset(amount=-{thick})")
            code_lines.append("    except Exception as _she:")
            code_lines.append(f'        print(f"Shell warning: {{_she}}")')

        elif f_type == "rib":
            thick = f.rib_thickness or f.thickness or 3.0
            pos = f.position or f.center
            px = pos.x if pos else 0.0
            py = pos.y if pos else 0.0
            pz = pos.z if pos else 0.0
            l = f.length or 30.0
            h = f.height or 20.0
            code_lines.append(f"    with Locations(({px}, {py}, {pz})):")
            code_lines.append(f"        Box(length={l}, width={thick}, height={h}, mode={mode})")

        elif f_type == "thread":
            dia = f.thread_diameter or f.diameter or 10.0
            rad = dia / 2.0
            length = f.thread_length or f.length or f.height or 30.0
            pitch = f.pitch or 1.5
            pos = f.position or f.center
            px = pos.x if pos else 0.0
            py = pos.y if pos else 0.0
            pz = pos.z if pos else 0.0
            code_lines.append(f"    with Locations(({px}, {py}, {pz})):")
            code_lines.append(f"        Cylinder(radius={rad}, height={length}, mode={mode})")
            code_lines.append("    try:")
            code_lines.append("        _top_edges = p.edges().sort_by(Axis.Z)[-1:]")
            code_lines.append("        if _top_edges:")
            code_lines.append(f"            chamfer(_top_edges, length=round({pitch} * 0.7, 2))")
            code_lines.append("    except Exception:")
            code_lines.append("        pass")

        code_lines.append("")

    code_lines.append("result = p.part")
    return "\n".join(code_lines) + "\n"


def _generate_sketch_code(
    sketch: CADIRSketchProfile, code_lines: List[str], indent: int = 4
):
    """Generate BuildSketch block for a given sketch profile."""
    sp = " " * indent
    plane = sketch.plane
    ox, oy, oz = plane.origin.x, plane.origin.y, plane.origin.z
    zx, zy, zz = plane.normal.x, plane.normal.y, plane.normal.z
    xx, xy, xz = plane.x_axis.x, plane.x_axis.y, plane.x_axis.z

    plane_expr = f"Plane(origin=({ox}, {oy}, {oz}), z_dir=({zx}, {zy}, {zz}), x_dir=({xx}, {xy}, {xz}))"
    code_lines.append(f"{sp}with BuildSketch({plane_expr}):")

    # Render outer primitives
    for prim in sketch.primitives:
        ptype = prim.primitive_type
        if ptype == "rectangle":
            cx, cy = prim.center.x, prim.center.y
            if cx == 0 and cy == 0:
                code_lines.append(
                    f"{sp}    Rectangle(width={prim.width}, height={prim.height})"
                )
            else:
                code_lines.append(
                    f"{sp}    with Locations(({cx}, {cy})): Rectangle(width={prim.width}, height={prim.height})"
                )
        elif ptype == "circle":
            cx, cy = prim.center.x, prim.center.y
            if cx == 0 and cy == 0:
                code_lines.append(f"{sp}    Circle(radius={prim.radius})")
            else:
                code_lines.append(
                    f"{sp}    with Locations(({cx}, {cy})): Circle(radius={prim.radius})"
                )
        elif ptype == "slot":
            cx, cy = prim.center.x, prim.center.y
            if cx == 0 and cy == 0:
                code_lines.append(
                    f"{sp}    SlotOverall(width={prim.length}, height={prim.width})"
                )
            else:
                code_lines.append(
                    f"{sp}    with Locations(({cx}, {cy})): SlotOverall(width={prim.length}, height={prim.width})"
                )
        elif ptype == "polygon":
            pts_str = ", ".join(f"({pt.x}, {pt.y})" for pt in prim.points)
            code_lines.append(f"{sp}    Polygon([{pts_str}])")
        elif ptype == "line":
            code_lines.append(
                f"{sp}    # Line primitive ({prim.start.x}, {prim.start.y}) -> ({prim.end.x}, {prim.end.y})"
            )

    # Render inner loops (holes in sketch)
    if sketch.inner_loops:
        for loop in sketch.inner_loops:
            code_lines.append(f"{sp}    with BuildSketch(mode=Mode.SUBTRACT):")
            for prim in loop:
                if prim.primitive_type == "circle":
                    code_lines.append(
                        f"{sp}        with Locations(({prim.center.x}, {prim.center.y})): Circle(radius={prim.radius})"
                    )
                elif prim.primitive_type == "rectangle":
                    code_lines.append(
                        f"{sp}        with Locations(({prim.center.x}, {prim.center.y})): Rectangle(width={prim.width}, height={prim.height})"
                    )


def interpret_and_execute(
    doc: CADIRDocument, design_id: str, timeout: int = 60
) -> Dict[str, Any]:
    """
    Deterministically compile CADIRDocument to build123d and execute via cad.executor.
    Returns executor result including STEP and STL paths.
    """
    from cad.executor import execute_cad_code

    code = generate_build123d_code(doc)
    exec_result = execute_cad_code(code, design_id=design_id, timeout=timeout)
    exec_result["cad_code"] = code
    return exec_result
