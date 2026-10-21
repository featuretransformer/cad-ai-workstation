from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
from pathlib import Path
from typing import List

from db.base import get_db
from db import crud, schemas

router = APIRouter()


@router.get("/{design_id}", response_model=List[schemas.ExportArtifactResponse])
def get_exports(design_id: UUID, db: Session = Depends(get_db)):
    """List available export artifacts (STEP, STL, GLB) for a design."""
    return crud.get_design_exports(db, design_id=design_id)


@router.get("/{design_id}/files", response_model=List[schemas.ExportArtifactResponse])
def get_exports_files(design_id: UUID, db: Session = Depends(get_db)):
    """Alias: List available export artifacts — matches frontend getExports call."""
    return crud.get_design_exports(db, design_id=design_id)


@router.get("/{design_id}/download/{fmt}")
def download_export(design_id: UUID, fmt: str, db: Session = Depends(get_db)):
    """Download exported CAD file (e.g. 'step', 'stl', 'glb')."""
    fmt_lower = fmt.lower()
    base_dir = Path(__file__).resolve().parent.parent.parent / "exports" / str(design_id)

    # 1. Python Parametric Script Download
    if fmt_lower in ("py", "python"):
        py_file = base_dir / "model_parametric.py"
        if not py_file.exists():
            design = crud.get_design(db, design_id=design_id)
            if design and design.cad_code:
                from cad.parametric_exporter import export_parametric_python_script
                export_parametric_python_script(str(design_id), design.prompt or "", design.cad_code, output_path=str(py_file))
        if py_file.exists():
            return FileResponse(
                path=str(py_file),
                filename=f"design_{str(design_id)[:8]}_parametric.py",
                media_type="text/x-python",
            )

    # 2. 2D Engineering Drawing Sheet Download
    if fmt_lower in ("drawing", "png", "sheet"):
        drawing_file = base_dir / "drawing_sheet.png"
        if not drawing_file.exists():
            stl_file = base_dir / "output.stl"
            if stl_file.exists():
                from cad.drawing_exporter import generate_drawing_sheet
                generate_drawing_sheet(stl_file, str(design_id), output_path=str(drawing_file))
        if drawing_file.exists():
            return FileResponse(
                path=str(drawing_file),
                filename=f"drawing_{str(design_id)[:8]}.png",
                media_type="image/png",
            )

    exports = crud.get_design_exports(db, design_id=design_id)

    matching = next((e for e in exports if e.format.lower() == fmt_lower), None)
    if not matching or not Path(matching.file_path).exists():
        candidate = base_dir / f"output.{fmt_lower}"
        if candidate.exists():
            return FileResponse(
                path=str(candidate),
                filename=f"design_{str(design_id)[:8]}.{fmt_lower}",
                media_type="application/octet-stream",
            )

        # On-demand synthesis if design exists in database
        design = crud.get_design(db, design_id=design_id)
        if design:
            step_candidate = base_dir / "output.step"
            stl_candidate = base_dir / "output.stl"

            # 1. Convert STEP/STL to GLB on the fly if needed
            if fmt_lower == "glb" and (step_candidate.exists() or stl_candidate.exists()):
                try:
                    from cad.exporter import generate_all_exports
                    new_exports = generate_all_exports(str(design_id), str(step_candidate), str(stl_candidate))
                    if "glb" in new_exports and Path(new_exports["glb"]).exists():
                        return FileResponse(
                            path=new_exports["glb"],
                            filename=f"design_{str(design_id)[:8]}.glb",
                            media_type="model/gltf-binary",
                        )
                except Exception as ce:
                    print(f"On-demand GLB conversion notice: {ce}")

            # 2. Run pipeline if no exports were generated yet
            if design.prompt:
                try:
                    from tasks.cad_tasks import run_cad_pipeline
                    run_cad_pipeline(str(design_id), design.prompt)
                    if candidate.exists():
                        return FileResponse(
                            path=str(candidate),
                            filename=f"design_{str(design_id)[:8]}.{fmt_lower}",
                            media_type="application/octet-stream",
                        )
                except Exception as pe:
                    print(f"On-demand pipeline execution notice: {pe}")

        raise HTTPException(status_code=404, detail=f"Export format '{fmt}' not found for design")

    return FileResponse(
        path=matching.file_path,
        filename=f"design_{str(design_id)[:8]}.{fmt_lower}",
        media_type="application/octet-stream",
    )
