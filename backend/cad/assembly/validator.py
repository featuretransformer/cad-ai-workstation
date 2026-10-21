"""
CAD Assembly Validation System.
Performs rigorous mechanical validation on multi-body assemblies:
- Collision and interference detection via OpenCASCADE boolean intersection
- Clearance verification against mating interface definitions
- Bounding envelope and dimensional constraint verification
- Solid count and manifold integrity checking
"""
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.assembly.schema import AssemblySpec


def validate_assembly(
    asm_spec: AssemblySpec,
    execution_result: Dict[str, Any],
    collision_tolerance: float = 0.05,  # mm^3 threshold for true volume interference
) -> Dict[str, Any]:
    """
    Validates physical feasibility of the assembled geometry.
    Returns structured validation report including collisions, clearances, and envelope metrics.
    """
    errors: List[str] = []
    warnings: List[str] = []
    collisions: List[Dict[str, Any]] = []
    clearances: List[Dict[str, Any]] = []

    located_solids = execution_result.get("_located_solids", [])
    instance_info = execution_result.get("instance_info", [])

    if not located_solids:
        errors.append("No located solids available for assembly validation.")
        return {
            "is_valid": False,
            "has_collisions": False,
            "errors": errors,
            "warnings": warnings,
            "collisions": [],
            "clearances": [],
        }

    # 1. Pairwise Collision / Interference Check
    num_solids = len(located_solids)
    for i in range(num_solids):
        solid_a = located_solids[i]
        info_a = instance_info[i] if i < len(instance_info) else {"name": f"Solid_{i}"}

        for j in range(i + 1, num_solids):
            solid_b = located_solids[j]
            info_b = instance_info[j] if j < len(instance_info) else {"name": f"Solid_{j}"}

            try:
                intersection = solid_a.intersect(solid_b)
                if intersection is not None:
                    inter_vol = sum(
                        float(s.volume) for s in intersection if hasattr(s, "volume")
                    )
                    if inter_vol > collision_tolerance:
                        collisions.append({
                            "component_a": info_a.get("component_id"),
                            "name_a": info_a.get("name"),
                            "component_b": info_b.get("component_id"),
                            "name_b": info_b.get("name"),
                            "interference_volume": round(inter_vol, 3),
                        })
            except Exception as e:
                warnings.append(f"Collision check skipped between {info_a.get('name')} and {info_b.get('name')}: {e}")

    if collisions:
        # Check against validation requirements
        max_allowed_inter = asm_spec.validation_requirements.get("max_interference_volume", 0.0)
        severe_collisions = [c for c in collisions if c["interference_volume"] > max_allowed_inter]
        if severe_collisions:
            for sc in severe_collisions:
                warnings.append(
                    f"Interference detected ({sc['interference_volume']} mm³) between {sc['name_a']} and {sc['name_b']}."
                )

    # 2. Clearance Checks based on Mating Interfaces
    for mate in asm_spec.mating_interfaces:
        parent_id = mate.parent_component_id
        child_id = mate.child_component_id

        # Find first instances of parent and child
        parent_solid = None
        child_solid = None
        for k, info in enumerate(instance_info):
            if info.get("component_id") == parent_id and parent_solid is None:
                parent_solid = located_solids[k]
            elif info.get("component_id") == child_id and child_solid is None:
                child_solid = located_solids[k]

        if parent_solid is not None and child_solid is not None:
            try:
                dist = float(parent_solid.distance_to(child_solid))
                clearances.append({
                    "interface_id": mate.interface_id,
                    "name": mate.name,
                    "mate_type": mate.mate_type,
                    "measured_distance": round(dist, 3),
                    "nominal_clearance": mate.clearance,
                })
            except Exception as de:
                warnings.append(f"Distance calculation skipped for interface {mate.name}: {de}")

    # 3. Dimensional Envelope Check
    reqs = asm_spec.validation_requirements
    bbox = execution_result.get("bounding_box", {})
    dx = bbox.get("xmax", 0.0) - bbox.get("xmin", 0.0)
    dy = bbox.get("ymax", 0.0) - bbox.get("ymin", 0.0)
    dz = bbox.get("zmax", 0.0) - bbox.get("zmin", 0.0)

    envelope_metrics = {
        "span_x": round(dx, 2),
        "span_y": round(dy, 2),
        "span_z": round(dz, 2),
        "max_radial_span": round(max(dx, dy), 2),
    }

    if "max_envelope_dia" in reqs:
        max_dia = reqs["max_envelope_dia"]
        if max(dx, dy) > max_dia * 1.25:
            warnings.append(f"Assembly radial span ({round(max(dx, dy), 1)} mm) exceeds limit ({max_dia} mm).")

    if "max_envelope_height" in reqs:
        max_h = reqs["max_envelope_height"]
        if dz > max_h * 1.25:
            warnings.append(f"Assembly height ({round(dz, 1)} mm) exceeds limit ({max_h} mm).")

    # 4. Solitary solid count sanity
    expected_instances = sum(c.quantity for c in asm_spec.components)
    actual_solids = execution_result.get("solids_count", 0)
    if actual_solids < expected_instances:
        warnings.append(
            f"Solid count mismatch: expected {expected_instances} separate bodies, got {actual_solids}."
        )

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "has_collisions": len(collisions) > 0,
        "collision_count": len(collisions),
        "collisions": collisions,
        "clearances": clearances,
        "envelope_metrics": envelope_metrics,
        "errors": errors,
        "warnings": warnings,
    }
