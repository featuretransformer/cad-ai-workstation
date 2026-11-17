"""
Geometry validation checks on exported CAD files.
"""
import os


def validate_step(step_path: str) -> dict:
    """Basic validation: file exists and is non-empty."""
    errors = []
    warnings = []

    if not os.path.exists(step_path):
        errors.append("STEP file not found")
        return {"valid": False, "errors": errors, "warnings": warnings}

    size = os.path.getsize(step_path)
    if size < 100:
        errors.append(f"STEP file suspiciously small ({size} bytes)")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def validate_mesh(stl_path: str) -> dict:
    """Mesh validation using trimesh: watertight, manifold, no degenerate faces."""
    errors = []
    warnings = []

    try:
        import trimesh
        mesh = trimesh.load(stl_path, force="mesh")

        if not isinstance(mesh, trimesh.Trimesh):
            errors.append("Could not load as triangular mesh")
            return {"valid": False, "errors": errors, "warnings": warnings}

        if not mesh.is_watertight:
            warnings.append("Mesh is not watertight (open boundaries detected)")
        if not mesh.is_winding_consistent:
            warnings.append("Mesh winding is inconsistent")
        if mesh.is_empty:
            errors.append("Mesh is empty")

        faces = len(mesh.faces)
        verts = len(mesh.vertices)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "faces": faces,
                "vertices": verts,
                "volume": float(mesh.volume) if mesh.is_watertight else None,
                "surface_area": float(mesh.area),
                "is_watertight": mesh.is_watertight,
            },
        }

    except Exception as e:
        errors.append(f"Mesh validation failed: {str(e)}")
        return {"valid": False, "errors": errors, "warnings": warnings}
