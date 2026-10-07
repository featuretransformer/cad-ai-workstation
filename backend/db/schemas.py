from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    name: str = "Untitled Session"


class SessionResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class DesignCreate(BaseModel):
    session_id: UUID
    prompt: str


class DesignResponse(BaseModel):
    id: UUID
    session_id: UUID
    version: int
    prompt: str
    status: str = "PENDING"
    cad_code: Optional[str] = None
    feature_tree: Dict[str, Any] = Field(default_factory=dict)
    geometry_valid: bool = False
    validation_errors: List[str] = Field(default_factory=list)
    validation_stats: Dict[str, Any] = Field(default_factory=dict)
    failure_reason: Optional[str] = None
    dfm_report: Dict[str, Any] = Field(default_factory=dict)
    engineering_report: Dict[str, Any] = Field(default_factory=dict)
    cost_estimate: Dict[str, Any] = Field(default_factory=dict)
    safety_report: Dict[str, Any] = Field(default_factory=dict)
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime
    model_config = {"from_attributes": True}


class AgentLogResponse(BaseModel):
    id: UUID
    design_id: UUID
    agent_name: str
    status: str
    message: Optional[str] = None
    confidence: float = 0.0
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    session_id: UUID
    prompt: str = Field(min_length=1, max_length=10000)


class GenerateResponse(BaseModel):
    task_id: str
    design_id: UUID
    message: str = "CAD generation started"


class ExportArtifactResponse(BaseModel):
    id: UUID
    design_id: UUID
    format: str
    file_path: str
    file_size_bytes: int
    created_at: datetime
    model_config = {"from_attributes": True}
