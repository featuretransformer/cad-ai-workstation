from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from db.base import get_db
from db import crud, schemas
from tasks.cad_tasks import run_cad_pipeline

router = APIRouter()


def _run_pipeline_sync(design_id: str, prompt: str):
    """Direct (non-Celery) runner for BackgroundTasks fallback."""
    run_cad_pipeline(design_id, prompt)


@router.post("/generate", response_model=schemas.GenerateResponse)
def generate_cad(
    data: schemas.GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Initiate CAD generation pipeline from a text prompt or engineering drawing description.
    """
    session = crud.get_session(db, session_id=data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    design = crud.create_design(db, session_id=data.session_id, prompt=data.prompt)

    task_id = str(design.id)
    try:
        # Try queueing through Celery
        celery_task = run_cad_pipeline.delay(str(design.id), data.prompt)
        task_id = celery_task.id
    except Exception as e:
        # Fallback to FastAPI BackgroundTasks if Celery/Redis is not running
        print(f"Celery dispatch failed: {e}. Executing via background task fallback.")
        # task_id stays as design.id so frontend can poll /task/{task_id}/status
        background_tasks.add_task(_run_pipeline_sync, str(design.id), data.prompt)

    return schemas.GenerateResponse(
        task_id=task_id,
        design_id=design.id,
        message="CAD generation pipeline initiated",
    )


@router.get("/task/{task_id}/status")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """
    Returns the status of a CAD pipeline task.
    In Celery mode task_id is the Celery task ID.
    In fallback/direct mode task_id equals design_id.
    """
    # Attempt design_id lookup first (fallback mode — task_id == design_id)
    try:
        design_uuid = UUID(task_id)
        design = crud.get_design(db, design_id=design_uuid)
        if design:
            return {
                "task_id": task_id,
                "status": getattr(design, "status", "PENDING"),
                "design_id": str(design.id),
            }
    except (ValueError, Exception):
        pass

    # Celery AsyncResult
    try:
        from tasks.celery_app import celery_app
        result = celery_app.AsyncResult(task_id)
        return {"task_id": task_id, "status": result.state, "design_id": None}
    except Exception as exc:
        return {"task_id": task_id, "status": "UNKNOWN", "error": str(exc)}


@router.get("/{design_id}", response_model=schemas.DesignResponse)
def get_design(design_id: UUID, db: Session = Depends(get_db)):
    """Get design details, CADIR model, and engineering reports."""
    design = crud.get_design(db, design_id=design_id)
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return design


@router.get("/{design_id}/logs", response_model=List[schemas.AgentLogResponse])
def get_design_logs(design_id: UUID, db: Session = Depends(get_db)):
    """Get execution logs for all agents involved in the design."""
    return crud.get_design_logs(db, design_id=design_id)