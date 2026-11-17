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
    images: Optional[List[Any]]          # multi-image list (sketch + photo + drawing)
    image_context: Optional[List[Any]]   # pre-processed images passed to downstream generators
    geometry_context: Optional[str]      # pre-computed mathematical coordinate grounding string
    file_path: Optional[str]
    clarification_needed: Optional[str]
    drawing_parse_error: Optional[str]
    cadir_document: Optional[Any]
    cadir_valid: bool
    cadir_errors: List[str]
    retrieved_examples: List[Dict[str, Any]]
    repair_attempts: int

    # Rich Design Intent (from intent_extractor.py)
    design_intent: Optional[Dict[str, Any]]  # full MechanicalDesignIntent dict

    # ─── CAD Asset Retrieval & Component Reuse Subsystem ──────────────
    retrieved_assets: List[Dict[str, Any]]
    reused_components: List[Dict[str, Any]]
    reference_assets: List[Dict[str, Any]]
    custom_components: List[Dict[str, Any]]
    retrieval_strategy: Dict[str, Any]

    # ─── Multi-Component Assembly Extensions (Roadmap Phases 1-5) ─────
    is_assembly: bool
    assembly_spec: Optional[Any]
    component_cadirs: Dict[str, Any]
    assembly_result: Dict[str, Any]
    assembly_validation: Dict[str, Any]
    design_plan: Dict[str, Any]

    # ─── Complex Prompt Decomposition Extensions ──────────────────────
    complexity_score: float
    is_complex_part: bool
    feature_build_plan: List[Dict[str, Any]]
    current_build_step: int
    cumulative_cadir: Optional[Any]
    build_step_results: List[Dict[str, Any]]
    decomposition_used: bool

    # ─── Deterministic Architectural Upgrades ─────────────────────────
    brep_state_summary: Optional[Dict[str, Any]]
    step_volumes: Optional[List[Dict[str, Any]]]
    visual_critique: Optional[Dict[str, Any]]
    macro_exemplars: Optional[List[Dict[str, Any]]]
    candidate_scores: Optional[List[Dict[str, Any]]]

    # ─── Verification Target & QA Judge Subsystem (P0 Upgrade) ────────
    cad_brief: Optional[Dict[str, Any]]
    verification_targets: Optional[List[Dict[str, Any]]]
    verification_receipt: Optional[Dict[str, Any]]
    judge_decision: Optional[Dict[str, Any]]
