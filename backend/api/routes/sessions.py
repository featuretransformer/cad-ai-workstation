from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from db.base import get_db
from db import crud, schemas

router = APIRouter()


@router.post("/", response_model=schemas.SessionResponse)
def create_session(data: schemas.SessionCreate, db: Session = Depends(get_db)):
    """Create a new CAD design session."""
    return crud.create_session(db, name=data.name)


@router.get("/", response_model=List[schemas.SessionResponse])
def list_sessions(limit: int = 50, db: Session = Depends(get_db)):
    """List recent design sessions."""
    return crud.list_sessions(db, limit=limit)


@router.get("/{session_id}", response_model=schemas.SessionResponse)
def get_session(session_id: UUID, db: Session = Depends(get_db)):
    """Get a specific session by ID."""
    session = crud.get_session(db, session_id=session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    """Delete a session."""
    if not crud.delete_session(db, session_id=session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": str(session_id)}


@router.get("/{session_id}/designs", response_model=List[schemas.DesignResponse])
def list_session_designs(session_id: UUID, db: Session = Depends(get_db)):
    """List all designs generated within a session."""
    return crud.list_designs(db, session_id=session_id)
