from sqlalchemy.orm import Session as DBSession
from uuid import UUID
from typing import List, Optional
from db import models


# ── Sessions ───────────────────────────────────────────────────────────
def create_session(db: DBSession, name: str = "Untitled Session") -> models.Session:
    session = models.Session(name=name)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DBSession, session_id: UUID) -> Optional[models.Session]:
    return db.query(models.Session).filter(models.Session.id == session_id).first()


def list_sessions(db: DBSession, limit: int = 50) -> List[models.Session]:
    return db.query(models.Session).order_by(models.Session.updated_at.desc()).limit(limit).all()


def delete_session(db: DBSession, session_id: UUID) -> bool:
    s = get_session(db, session_id)
    if s:
        db.delete(s)
        db.commit()
        return True
    return False


# ── Designs ────────────────────────────────────────────────────────────
def create_design(db: DBSession, session_id: UUID, prompt: str) -> models.Design:
    # Get next version number
    count = db.query(models.Design).filter(models.Design.session_id == session_id).count()
    design = models.Design(session_id=session_id, prompt=prompt, version=count + 1)
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


def get_design(db: DBSession, design_id: UUID) -> Optional[models.Design]:
    return db.query(models.Design).filter(models.Design.id == design_id).first()


def update_design(db: DBSession, design_id: UUID, **kwargs) -> Optional[models.Design]:
    design = get_design(db, design_id)
    if design:
        for k, v in kwargs.items():
            setattr(design, k, v)
        db.commit()
        db.refresh(design)
    return design


def list_designs(db: DBSession, session_id: UUID) -> List[models.Design]:
    return db.query(models.Design).filter(
        models.Design.session_id == session_id
    ).order_by(models.Design.version.desc()).all()


# ── Agent Logs ─────────────────────────────────────────────────────────
def create_agent_log(db: DBSession, design_id: UUID, agent_name: str,
                     status: str, message: str = "", confidence: float = 0.0,
                     payload: dict = None) -> models.AgentLog:
    log = models.AgentLog(
        design_id=design_id, agent_name=agent_name,
        status=status, message=message,
        confidence=confidence, payload=payload or {}
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_design_logs(db: DBSession, design_id: UUID) -> List[models.AgentLog]:
    return db.query(models.AgentLog).filter(
        models.AgentLog.design_id == design_id
    ).order_by(models.AgentLog.created_at).all()


# ── Export Artifacts ───────────────────────────────────────────────────
def create_export(db: DBSession, design_id: UUID, format: str,
                  file_path: str, file_size: int = 0) -> models.ExportArtifact:
    artifact = models.ExportArtifact(
        design_id=design_id, format=format,
        file_path=file_path, file_size_bytes=file_size
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def get_design_exports(db: DBSession, design_id: UUID) -> List[models.ExportArtifact]:
    return db.query(models.ExportArtifact).filter(
        models.ExportArtifact.design_id == design_id
    ).all()
