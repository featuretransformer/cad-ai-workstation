from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class SessionCreate(BaseModel):
    name: str = "Untitled Session"


class SessionResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DesignCreate(BaseModel):
    session_id: UUID
    prompt: str


class DesignResponse(BaseModel):
    id: UUID
    session_id: UUID
    version: int
    prompt: str
    image_data_b64: List[str] = []
    status: str = "PENDING"
    cad_code: Optional[str] = None
    feature_tree: Dict[str, Any] = {}
    geometry_valid: bool = False
    dfm_report: Dict[str, Any] = {}
    engineering_report: Dict[str, Any] = {}
    cost_estimate: Dict[str, Any] = {}
    safety_report: Dict[str, Any] = {}
    alternatives: List[Dict[str, Any]] = []
    confidence_scores: Dict[str, float] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class AgentLogResponse(BaseModel):
    id: UUID
    design_id: UUID
    agent_name: str
    status: str
    message: Optional[str] = None
    confidence: float = 0.0
    payload: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateRequest(BaseModel):
    session_id: UUID
    prompt: str
    # Optional images as base64-encoded strings (data URLs or raw base64).
    # Each entry may be "data:image/png;base64,..." or a raw base64 string.
    # Up to 3 images are processed by the multimodal intent extractor.
    images: Optional[List[str]] = None


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

    class Config:
        from_attributes = True
