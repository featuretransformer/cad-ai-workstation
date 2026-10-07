"""
Agent State Schema for LangGraph CAD generation pipeline.
Maintains 100% backward compatibility with existing cad_tasks.py pipeline
while extending state with CADIR canonical representation and retrieval fields.
"""
from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict, total=False):
    # ─── Core Workflow Metadata ───────────────────────────────────────
    design_id: str
    session_id: str
    user_prompt: str
    parsed_intent: Dict[str, Any]

    # ─── CAD Code & Execution State ───────────────────────────────────
    cad_code: str
    cad_script_history: List[str]
    execution_result: Dict[str, Any]
    feature_tree: Dict[str, Any]
    export_paths: Dict[str, str]

    # ─── Geometry & Validation State ──────────────────────────────────
    geometry_valid: bool
    validation_errors: List[str]
    validation_stats: Dict[str, Any]

    # ─── Downstream Engineering Reports ──────────────────────────────
    dfm_report: Dict[str, Any]
    engineering_report: Dict[str, Any]
    cost_estimate: Dict[str, Any]
    safety_report: Dict[str, Any]
    cam_report: Dict[str, Any]
    doc_report: Dict[str, Any]
    alternatives: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]

    # ─── Error Handling & Loop Control ────────────────────────────────
    error_count: int
    max_retries: int
    last_error: str
    messages: List[Dict[str, Any]]

    # ─── CADIR Canonical Extensions (Target Architecture) ─────────────
    input_type: str
    image_data: Optional[Any]
    file_path: Optional[str]
    clarification_needed: Optional[str]
    drawing_parse_error: Optional[str]
    cadir_document: Optional[Any]
    cadir_valid: bool
    cadir_errors: List[str]
    retrieved_examples: List[Dict[str, Any]]
    repair_attempts: int

