import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), default="Untitled Session")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    designs = relationship("Design", back_populates="session", cascade="all, delete-orphan")


class Design(Base):
    __tablename__ = "designs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    version = Column(Integer, default=1)
    prompt = Column(Text, nullable=False)
    cad_code = Column(Text)
    feature_tree = Column(JSON, default={})
    geometry_valid = Column(Boolean, default=False)
    dfm_report = Column(JSON, default={})
    engineering_report = Column(JSON, default={})
    cost_estimate = Column(JSON, default={})
    safety_report = Column(JSON, default={})
    alternatives = Column(JSON, default=[])
    confidence_scores = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=utcnow)
    session = relationship("Session", back_populates="designs")
    agent_logs = relationship("AgentLog", back_populates="design", cascade="all, delete-orphan")
    export_artifacts = relationship("ExportArtifact", back_populates="design", cascade="all, delete-orphan")


class AgentLog(Base):
    __tablename__ = "agent_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"))
    agent_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # running | done | error
    message = Column(Text)
    confidence = Column(Float, default=0.0)
    payload = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=utcnow)
    design = relationship("Design", back_populates="agent_logs")


class ExportArtifact(Base):
    __tablename__ = "export_artifacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"))
    format = Column(String(20), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    design = relationship("Design", back_populates="export_artifacts")
