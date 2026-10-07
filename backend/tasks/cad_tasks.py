"""Celery task for the CAD generation pipeline and durable status updates."""
import json
import redis
from celery import Task
from tasks.celery_app import celery_app
from agents.graph import cad_graph
from agents.state import AgentState
from config import get_settings
from db.base import SessionLocal
from db import crud
from cad.exporter import get_file_size

settings = get_settings()
AGENT_DISPLAY = {"input_classifier": "Input Classifier", "supervisor": "Supervisor", "design_agent": "Design Agent", "cadir_validator": "CADIR Validator", "interpreter": "CADIR Interpreter", "cad_executor": "CAD Executor", "geometry_validator": "Geometry Validator", "cadir_repair": "CADIR Repair Agent", "dfm_agent": "DFM Analyst", "engineering_agent": "Engineering Agent", "cost_agent": "Cost Estimator", "safety_agent": "Safety Agent", "alternatives_agent": "Alternatives Agent", "cam_agent": "CAM Agent", "doc_agent": "Documentation Agent"}


def publish_event(r, design_id: str, event: dict):
    if r is not None:
        try:
            r.publish(f"design:{design_id}:events", json.dumps(event))
        except Exception:
            pass


@celery_app.task(bind=True, name="tasks.cad_tasks.run_cad_pipeline", max_retries=0)
def run_cad_pipeline(self: Task, design_id: str, prompt: str):
    r = None
    try:
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
    except Exception:
        pass
    db = SessionLocal()
    final_state = {}
    try:
        crud.update_design(db, design_id, status="IN_PROGRESS", failure_reason=None)
        publish_event(r, design_id, {"type": "pipeline_started", "design_id": design_id, "status": "IN_PROGRESS", "message": "Starting AI-native CAD pipeline..."})
        initial_state: AgentState = {"design_id": design_id, "session_id": "", "user_prompt": prompt, "parsed_intent": {}, "cad_code": "", "cad_script_history": [], "execution_result": {}, "feature_tree": {}, "export_paths": {}, "geometry_valid": False, "validation_errors": [], "validation_stats": {}, "dfm_report": {}, "engineering_report": {}, "cost_estimate": {}, "safety_report": {}, "cam_report": {}, "doc_report": {}, "alternatives": [], "confidence_scores": {}, "error_count": 0, "max_retries": settings.max_retries, "last_error": "", "messages": []}
        final_state = dict(initial_state)
        for event in cad_graph.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                if isinstance(node_output, dict): final_state.update(node_output)
                confidence = node_output.get("confidence_scores", {}).get(node_name, 0)
                payload = _safe_payload(node_name, node_output)
                publish_event(r, design_id, {"type": "agent_update", "design_id": design_id, "agent": node_name, "display_name": AGENT_DISPLAY.get(node_name, node_name), "status": "done", "confidence": confidence, "payload": payload})
                try: crud.create_agent_log(db, design_id, node_name, "done", message=_agent_message(node_name, node_output), confidence=confidence, payload=payload)
                except Exception: db.rollback()
        errors = final_state.get("validation_errors", [])
        valid = bool(final_state.get("geometry_valid", False))
        update_data = {"geometry_valid": valid, "validation_errors": errors, "validation_stats": final_state.get("validation_stats", {}), "failure_reason": None}
        for field in ["cad_code", "feature_tree", "dfm_report", "engineering_report", "cost_estimate", "safety_report", "alternatives", "confidence_scores"]:
            if final_state.get(field): update_data[field] = final_state[field]
        for fmt, path in final_state.get("export_paths", {}).items():
            try: crud.create_export(db, design_id, fmt, path, get_file_size(path))
            except Exception: db.rollback()
        if not valid:
            reason = "; ".join(errors) or final_state.get("last_error") or "Geometry validation failed"
            update_data.update(status="FAILED", failure_reason=reason)
            crud.update_design(db, design_id, **update_data)
            publish_event(r, design_id, {"type": "pipeline_error", "design_id": design_id, "status": "FAILED", "geometry_valid": False, "error": reason})
            return {"status": "failed", "design_id": design_id, "geometry_valid": False, "error": reason}
        update_data["status"] = "COMPLETE"
        crud.update_design(db, design_id, **update_data)
        publish_event(r, design_id, {"type": "pipeline_complete", "design_id": design_id, "status": "COMPLETE", "geometry_valid": True, "export_paths": final_state.get("export_paths", {}), "confidence_scores": final_state.get("confidence_scores", {}), "message": "Pipeline complete!"})
        return {"status": "complete", "design_id": design_id, "geometry_valid": True}
    except Exception as exc:
        db.rollback(); reason = str(exc)
        try: crud.update_design(db, design_id, status="FAILED", geometry_valid=False, validation_errors=final_state.get("validation_errors", []), validation_stats=final_state.get("validation_stats", {}), failure_reason=reason)
        except Exception: db.rollback()
        publish_event(r, design_id, {"type": "pipeline_error", "design_id": design_id, "status": "FAILED", "error": reason})
        raise
    finally:
        db.close()
        if r is not None:
            try: r.close()
            except Exception: pass


def _safe_payload(node_name: str, output: dict) -> dict:
    if node_name == "supervisor": return {"parsed_intent": output.get("parsed_intent", {})}
    if node_name == "design_agent":
        code = output.get("cad_code", ""); return {"code_preview": code[:200] + "..." if len(code) > 200 else code}
    if node_name == "geometry_validator": return {"valid": output.get("geometry_valid", False), "errors": output.get("validation_errors", []), "stats": output.get("validation_stats", {})}
    if node_name == "dfm_agent": return {"score": output.get("dfm_report", {}).get("overall_score", 0), "issues": len(output.get("dfm_report", {}).get("issues", []))}
    if node_name == "cost_agent": return {"unit_cost": output.get("cost_estimate", {}).get("total_unit_cost_usd", 0)}
    return {}


def _agent_message(node_name: str, output: dict) -> str:
    if node_name == "supervisor": return f"Parsed intent: {output.get('parsed_intent', {}).get('summary', '')}"
    if node_name == "geometry_validator": return "Geometry valid ✓" if output.get("geometry_valid", False) else f"Errors: {'; '.join(output.get('validation_errors', []))}"
    if node_name == "dfm_agent": return f"DFM score: {output.get('dfm_report', {}).get('overall_score', 0)}/100"
    if node_name == "cost_agent": return f"Estimated unit cost: ${output.get('cost_estimate', {}).get('total_unit_cost_usd', 0):.2f}"
    return f"{AGENT_DISPLAY.get(node_name, node_name)} completed"
