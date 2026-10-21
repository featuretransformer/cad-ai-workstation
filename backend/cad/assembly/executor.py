"""
CAD Assembly Executor.
Executes multi-component assemblies using build123d:
- Builds individual components from CADIR documents
- Applies 3D spatial placements (translations and Euler rotations)
- Assembles multi-body compounds retaining distinct solid entities
- Exports assembly STEP, combined STL, GLB preview, and per-component STLs
"""
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import os
import sys
import json
import logging

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.assembly.schema import AssemblySpec, ComponentSpec, Placement3D
from cad.cadir.interpreter import generate_build123d_code
from cad.assembly.component_generator import generate_component_cadir
from cad.exporter import generate_all_exports

logger = logging.getLogger(__name__)
EXPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "exports"


def _build_part_from_cadir(doc) -> Any:
    """Executes a CADIR document in-process to obtain the build123d Shape."""
    from build123d import (
        BuildPart, BuildSketch, Mode, Box, Cylinder, Sphere, Hole, CounterBoreHole,
        CounterSinkHole, Plane, Axis, Location, Locations, extrude, revolve,
        fillet, chamfer, Rectangle, Circle, SlotOverall, Polygon, RegularPolygon
    )

    code = generate_build123d_code(doc)
    local_scope: Dict[str, Any] = {}
    global_scope: Dict[str, Any] = {
        "BuildPart": BuildPart,
        "BuildSketch": BuildSketch,
        "Mode": Mode,
        "Box": Box,
        "Cylinder": Cylinder,
        "Sphere": Sphere,
        "Hole": Hole,
        "CounterBoreHole": CounterBoreHole,
        "CounterSinkHole": CounterSinkHole,
        "Plane": Plane,
        "Axis": Axis,
        "Location": Location,
        "Locations": Locations,
        "extrude": extrude,
        "revolve": revolve,
        "fillet": fillet,
        "chamfer": chamfer,
        "Rectangle": Rectangle,
        "Circle": Circle,
        "SlotOverall": SlotOverall,
        "Polygon": Polygon,
        "RegularPolygon": RegularPolygon,
    }

    exec(code, global_scope, local_scope)
    result = local_scope.get("result")
    if result is None:
        raise ValueError(f"Execution of component {doc.name} did not produce a 'result' geometry.")
    return result


def execute_assembly(
    asm_spec: AssemblySpec,
    design_id: str,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes all component CADIRs, applies instance placements, builds a compound assembly,
    and produces multi-body STEP, STL, GLB, and per-part STL exports.
    """
    from build123d import Location, Compound, export_step, export_stl, export_gltf

    out_dir = Path(output_dir) if output_dir else EXPORTS_DIR / design_id
    out_dir.mkdir(parents=True, exist_ok=True)

    located_solids = []
    instance_info = []
    component_exports = {}
    component_solids = {}
    code_snippets = []

    # 1. Build and locate each component instance
    for comp in asm_spec.components:
        if comp.cadir_document is None:
            comp.cadir_document = generate_component_cadir(comp, asm_spec)

        # Build base part
        base_part = _build_part_from_cadir(comp.cadir_document)
        component_solids[comp.component_id] = base_part

        # Export individual component STL
        comp_stl_path = str(out_dir / f"comp_{comp.component_id}.stl")
        try:
            export_stl(base_part, comp_stl_path)
            component_exports[comp.component_id] = comp_stl_path
        except Exception as e:
            logger.warning(f"Could not export STL for component {comp.name}: {e}")

        # Record component code snippet
        comp_code = generate_build123d_code(comp.cadir_document)
        code_snippets.append(f"# === Component: {comp.name} ({comp.component_id}) ===\n{comp_code}")

        # Place each instance
        placements = comp.instance_placements or [comp.base_placement]
        for idx in range(comp.quantity):
            pl = placements[idx] if idx < len(placements) else comp.base_placement
            tx, ty, tz = pl.translation.x, pl.translation.y, pl.translation.z
            rx, ry, rz = pl.rotation.x, pl.rotation.y, pl.rotation.z

            loc = Location((tx, ty, tz), (rx, ry, rz))
            located_part = base_part.located(loc)
            located_solids.append(located_part)

            instance_info.append({
                "component_id": comp.component_id,
                "name": f"{comp.name} #{idx+1}",
                "role": comp.role,
                "instance_index": idx + 1,
                "placement": {
                    "translation": [tx, ty, tz],
                    "rotation": [rx, ry, rz],
                },
                "volume": float(located_part.volume) if hasattr(located_part, "volume") else 0.0,
            })

    if not located_solids:
        return {
            "success": False,
            "error": "No component solids were generated for the assembly.",
        }

    # 2. Build multi-solid compound
    assembly_compound = Compound(located_solids)

    # 3. Export Multi-Body Files
    step_path = str(out_dir / "output.step")
    stl_path = str(out_dir / "output.stl")
    glb_path = str(out_dir / "output.glb")

    export_step(assembly_compound, step_path)
    export_stl(assembly_compound, stl_path)

    # Try native GLB export via build123d
    glb_success = False
    try:
        glb_res = export_gltf(assembly_compound, glb_path, binary=True)
        glb_success = bool(glb_res and os.path.exists(glb_path))
    except Exception as ge:
        logger.warning(f"Native GLB export notice: {ge}")

    # Fallback to general export pipeline if needed
    all_exports = generate_all_exports(design_id, step_path, stl_path)
    if "glb" in all_exports and os.path.exists(all_exports["glb"]):
        glb_path = all_exports["glb"]
        glb_success = True

    # 4. Compute Assembly Bounding Box & Mass Properties
    bb = assembly_compound.bounding_box()
    total_volume = float(assembly_compound.volume) if hasattr(assembly_compound, "volume") else sum(i["volume"] for i in instance_info)

    # 5. Save generated assembly script
    assembly_script = "\n".join([
        '"""',
        f'Assembly: {asm_spec.name} (ID: {asm_spec.id})',
        f'Total Components: {len(asm_spec.components)}, Total Instances: {len(located_solids)}',
        '"""',
        'from build123d import *',
        '',
        *code_snippets,
        '',
        '# --- Assembly Placement & Compound Construction ---',
        f'# Assembled {len(located_solids)} solids into Compound',
    ])
    script_path = str(out_dir / "assembly_script.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(assembly_script)

    return {
        "success": True,
        "assembly_id": asm_spec.id,
        "name": asm_spec.name,
        "volume": total_volume,
        "solids_count": len(assembly_compound.solids()),
        "instances_count": len(located_solids),
        "bounding_box": {
            "xmin": float(bb.min.X),
            "xmax": float(bb.max.X),
            "ymin": float(bb.min.Y),
            "ymax": float(bb.max.Y),
            "zmin": float(bb.min.Z),
            "zmax": float(bb.max.Z),
        },
        "step_path": step_path,
        "stl_path": stl_path,
        "glb_path": glb_path if glb_success else None,
        "export_paths": {
            "step": step_path,
            "stl": stl_path,
            **({"glb": glb_path} if glb_success else {}),
        },
        "component_exports": component_exports,
        "instance_info": instance_info,
        "assembly_script_path": script_path,
        "cad_code": assembly_script,
        "_assembly_compound": assembly_compound,
        "_located_solids": located_solids,
        "_component_solids": component_solids,
    }
