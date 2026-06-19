"""
CAD file exporters: STEP → STL → GLB conversion pipeline.
"""
import os
import json
from pathlib import Path


def step_to_glb(step_path: str, glb_path: str) -> bool:
    """Convert STEP to GLB via trimesh."""
    try:
        import trimesh
        mesh = trimesh.load(step_path)
        if hasattr(mesh, "dump"):
            scene = mesh
        else:
            scene = trimesh.scene.scene.Scene(geometry={"mesh": mesh})
        scene.export(glb_path, file_type="glb")
        return True
    except Exception as e:
        print(f"GLB conversion failed: {e}")
        return False


def stl_to_glb(stl_path: str, glb_path: str) -> bool:
    """Fallback: convert STL to GLB."""
    try:
        import trimesh
        mesh = trimesh.load(stl_path)
        scene = trimesh.scene.scene.Scene(geometry={"mesh": mesh})
        scene.export(glb_path, file_type="glb")
        return True
    except Exception as e:
        print(f"STL→GLB conversion failed: {e}")
        return False


def generate_all_exports(design_id: str, step_path: str, stl_path: str) -> dict:
    """
    Given STEP + STL paths, generate GLB and return all file paths.
    """
    from pathlib import Path
    base_dir = Path(step_path).parent

    glb_path = str(base_dir / "output.glb")
    export_paths = {
        "step": step_path,
        "stl": stl_path,
    }

    # Try STEP → GLB first, fallback to STL → GLB
    if os.path.exists(step_path):
        if step_to_glb(step_path, glb_path):
            export_paths["glb"] = glb_path
    elif os.path.exists(stl_path):
        if stl_to_glb(stl_path, glb_path):
            export_paths["glb"] = glb_path

    return export_paths


def get_file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0
