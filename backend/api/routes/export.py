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
    exports = crud.get_design_exports(db, design_id=design_id)

    matching = next((e for e in exports if e.format.lower() == fmt_lower), None)
    if not matching or not Path(matching.file_path).exists():
        # Fallback check directly in exports dir
        base_dir = Path(__file__).resolve().parent.parent.parent / "exports" / str(design_id)
        candidate = base_dir / f"output.{fmt_lower}"
        if candidate.exists():
            return FileResponse(
                path=str(candidate),
                filename=f"design_{str(design_id)[:8]}.{fmt_lower}",
                media_type="application/octet-stream",
            )
        raise HTTPException(status_code=404, detail=f"Export format '{fmt}' not found for design")

    return FileResponse(
        path=matching.file_path,
        filename=f"design_{str(design_id)[:8]}.{fmt_lower}",
        media_type="application/octet-stream",
    )
