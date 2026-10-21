"""
CAD file exporters: STEP → STL → GLB conversion pipeline.
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def step_to_glb(step_path: str, glb_path: str) -> bool:
    """Convert STEP to GLB via build123d native GLTF export."""
    try:
        from build123d import import_step, export_gltf
        shape = import_step(step_path)
        result = export_gltf(shape, glb_path, binary=True)
        if result:
            logger.info("STEP→GLB conversion succeeded: %s", glb_path)
        return bool(result)
    except ImportError:
        logger.warning("GLB conversion skipped: build123d not installed or export_gltf unavailable.")
        return False
    except Exception as e:
        logger.warning("GLB conversion failed: %s", e)
        return False


def stl_to_glb(stl_path: str, glb_path: str) -> bool:
    """Fallback: convert STL to GLB via trimesh."""
    try:
        import trimesh
        mesh = trimesh.load(stl_path, force="mesh")
        if mesh is None or (hasattr(mesh, "is_empty") and mesh.is_empty):
            logger.warning("STL→GLB: loaded mesh is empty — skipping export.")
            return False
        # Export as scene for GLB compatibility
        if hasattr(mesh, "scene"):
            scene = mesh.scene()
        else:
            scene = trimesh.scene.scene.Scene(geometry={"mesh": mesh})
        scene.export(glb_path, file_type="glb")
        logger.info("STL→GLB conversion succeeded: %s", glb_path)
        return True
    except ImportError:
        logger.warning("STL→GLB skipped: trimesh not installed.")
        return False
    except Exception as e:
        logger.warning("STL→GLB conversion failed: %s", e)
        return False


def generate_all_exports(
    design_id: str,
    step_path: str,
    stl_path: str,
    prompt: str = "",
    cad_code: str = "",
    parameters: dict = None,
) -> dict:
    """
    Given STEP + STL paths, generates GLB, 2D technical drawing sheet,
    and standalone parametric Python script.
    """
    base_dir = Path(step_path).parent
    glb_path = str(base_dir / "output.glb")
    drawing_path = str(base_dir / "drawing_sheet.png")
    py_path = str(base_dir / "model_parametric.py")

    export_paths = {
        "step": step_path,
        "stl": stl_path,
    }

    glb_success = False

    # Attempt 1: STEP → GLB
    if os.path.exists(step_path):
        glb_success = step_to_glb(step_path, glb_path)
    else:
        logger.warning("STEP file not found, skipping STEP→GLB: %s", step_path)

    # Attempt 2: STL → GLB (fallback)
    if not glb_success and os.path.exists(stl_path):
        logger.info("Falling back to STL→GLB for design %s", design_id)
        glb_success = stl_to_glb(stl_path, glb_path)
    elif not glb_success:
        logger.warning("STL file not found, cannot produce GLB: %s", stl_path)

    if glb_success:
        export_paths["glb"] = glb_path
    else:
        logger.warning("GLB output unavailable for design %s — viewers will use STL fallback.", design_id)

    # Attempt 3: 2D Engineering Drawing Sheet
    try:
        from cad.drawing_exporter import generate_drawing_sheet
        if os.path.exists(stl_path):
            drw = generate_drawing_sheet(stl_path, design_id=design_id, title=prompt or "Mechanical Component", output_path=drawing_path)
            if drw and os.path.exists(drw):
                export_paths["drawing"] = drw
    except Exception as de:
        logger.warning("Drawing sheet generation failed: %s", de)

    # Attempt 4: Parametric Python Script
    try:
        from cad.parametric_exporter import export_parametric_python_script
        if cad_code:
            p_script = export_parametric_python_script(design_id, prompt, cad_code, parameters=parameters, output_path=py_path)
            if p_script and os.path.exists(py_path):
                export_paths["python"] = py_path
    except Exception as pe:
        logger.warning("Parametric script export failed: %s", pe)

    return export_paths


def get_file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0
