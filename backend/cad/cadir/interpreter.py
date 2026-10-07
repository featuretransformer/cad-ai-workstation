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
            cx = f.center.x if f.center else 0.0
            cy = f.center.y if f.center else 0.0
            cz = f.center.z if f.center else 0.0
            if cx == 0 and cy == 0 and cz == 0:
                code_lines.append(
                    f"    Box(length={f.length}, width={f.width}, height={f.height}, mode={mode})"
                )
            else:
                code_lines.append(f"    with Locations(({cx}, {cy}, {cz})):")
                code_lines.append(
                    f"        Box(length={f.length}, width={f.width}, height={f.height}, mode={mode})"
                )

        elif f_type == "cylinder":
            cx = f.center.x if f.center else 0.0
            cy = f.center.y if f.center else 0.0
            cz = f.center.z if f.center else 0.0
            if cx == 0 and cy == 0 and cz == 0:
                code_lines.append(
                    f"    Cylinder(radius={f.radius}, height={f.height}, mode={mode})"
                )
            else:
                code_lines.append(f"    with Locations(({cx}, {cy}, {cz})):")
                code_lines.append(
                    f"        Cylinder(radius={f.radius}, height={f.height}, mode={mode})"
                )

        elif f_type == "sphere":
            cx = f.center.x if f.center else 0.0
            cy = f.center.y if f.center else 0.0
            cz = f.center.z if f.center else 0.0
            if cx == 0 and cy == 0 and cz == 0:
                code_lines.append(f"    Sphere(radius={f.radius}, mode={mode})")
            else:
                code_lines.append(f"    with Locations(({cx}, {cy}, {cz})):")
                code_lines.append(f"        Sphere(radius={f.radius}, mode={mode})")

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

        elif f_type == "hole":
            px = f.position.x if f.position else 0.0
            py = f.position.y if f.position else 0.0
            pz = f.position.z if f.position else 0.0
            rad = f.diameter / 2.0
            dep = f.depth or 10.0

            code_lines.append(f"    with Locations(({px}, {py}, {pz})):")
            if f.hole_type == "counterbore" and f.cbore_diameter and f.cbore_depth:
                cb_r = f.cbore_diameter / 2.0
                code_lines.append(
                    f"        CounterBoreHole(radius={rad}, counter_bore_radius={cb_r}, counter_bore_depth={f.cbore_depth}, depth={dep})"
                )
            elif f.hole_type == "countersink" and f.csink_diameter:
                cs_r = f.csink_diameter / 2.0
                code_lines.append(
                    f"        CounterSinkHole(radius={rad}, counter_sink_radius={cs_r}, depth={dep})"
                )
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
