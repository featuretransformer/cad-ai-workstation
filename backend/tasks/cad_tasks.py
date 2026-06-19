"""
Celery CAD generation task — runs the full LangGraph pipeline
and publishes real-time events to Redis for WebSocket streaming.
"""
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

# Agent display names for UI
AGENT_DISPLAY = {
    "supervisor": "Supervisor",
    "design_agent": "Design Agent",
    "cad_executor": "CAD Executor",
    "geometry_validator": "Geometry Validator",
    "dfm_agent": "DFM Analyst",
    "engineering_agent": "Engineering Agent",
    "cost_agent": "Cost Estimator",
    "safety_agent": "Safety Agent",
    "alternatives_agent": "Alternatives Agent",
    "cam_agent": "CAM Agent",
    "doc_agent": "Documentation Agent",
}


def publish_event(r: redis.Redis, design_id: str, event: dict):
    """Publish an event to the design's Redis channel."""
    channel = f"design:{design_id}:events"
    r.publish(channel, json.dumps(event))


@celery_app.task(bind=True, name="tasks.cad_tasks.run_cad_pipeline", max_retries=0)
def run_cad_pipeline(self: Task, design_id: str, prompt: str):
    """Main CAD generation pipeline task."""
    r = redis.from_url(settings.redis_url)
    db = SessionLocal()

    try:
        publish_event(r, design_id, {
            "type": "pipeline_started",
            "design_id": design_id,
            "message": "Starting AI-native CAD pipeline...",
        })

        # Initial LangGraph state
        initial_state: AgentState = {
            "design_id": design_id,
            "session_id": "",
            "user_prompt": prompt,
            "parsed_intent": {},
            "cad_code": "",
            "cad_script_history": [],
            "execution_result": {},
            "feature_tree": {},
            "export_paths": {},
            "geometry_valid": False,
            "validation_errors": [],
            "validation_stats": {},
            "dfm_report": {},
            "engineering_report": {},
            "cost_estimate": {},
            "safety_report": {},
            "cam_report": {},
            "doc_report": {},
            "alternatives": [],
            "confidence_scores": {},
            "error_count": 0,
            "max_retries": settings.max_retries,
            "last_error": "",
            "messages": [],
        }

        # Stream agent events as graph executes
        for event in cad_graph.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                display_name = AGENT_DISPLAY.get(node_name, node_name)
                confidence = node_output.get("confidence_scores", {}).get(node_name, 0)

                # Publish agent progress
                publish_event(r, design_id, {
                    "type": "agent_update",
                    "agent": node_name,
                    "display_name": display_name,
                    "status": "done",
                    "confidence": confidence,
                    "payload": _safe_payload(node_name, node_output),
                })

                # Persist agent log to DB
                try:
                    crud.create_agent_log(
                        db, design_id, node_name, "done",
                        message=_agent_message(node_name, node_output),
                        confidence=confidence,
                        payload=_safe_payload(node_name, node_output),
                    )
                except Exception:
                    pass

        # Get final state
        final_state = cad_graph.invoke(initial_state) if False else _get_final_state(initial_state, r, design_id)

        # Update design record in DB
        try:
            update_data = {}
            if final_state.get("cad_code"):
                update_data["cad_code"] = final_state["cad_code"]
            if final_state.get("feature_tree"):
                update_data["feature_tree"] = final_state["feature_tree"]
            if "geometry_valid" in final_state:
                update_data["geometry_valid"] = final_state["geometry_valid"]
            for field in ["dfm_report", "engineering_report", "cost_estimate", "safety_report", "alternatives", "confidence_scores"]:
                if final_state.get(field):
                    update_data[field] = final_state[field]

            if update_data:
                crud.update_design(db, design_id, **update_data)

            # Save export artifacts
            for fmt, path in final_state.get("export_paths", {}).items():
                try:
                    size = get_file_size(path)
                    crud.create_export(db, design_id, fmt, path, size)
                except Exception:
                    pass
        except Exception as e:
            print(f"DB update error: {e}")

        # Final event
        publish_event(r, design_id, {
            "type": "pipeline_complete",
            "design_id": design_id,
            "geometry_valid": final_state.get("geometry_valid", False),
            "export_paths": final_state.get("export_paths", {}),
            "confidence_scores": final_state.get("confidence_scores", {}),
            "message": "Pipeline complete!" if final_state.get("geometry_valid") else "Pipeline failed — check agent log",
        })

        return {"status": "complete", "design_id": design_id}

    except Exception as e:
        publish_event(r, design_id, {
            "type": "pipeline_error",
            "design_id": design_id,
            "error": str(e),
        })
        raise
    finally:
        db.close()
        r.close()


def _get_final_state(initial_state: AgentState, r, design_id: str) -> dict:
    """Run the graph and collect the final state."""
    final = dict(initial_state)
    for event in cad_graph.stream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            final.update(node_output)
    return final


def _safe_payload(node_name: str, output: dict) -> dict:
    """Extract a safe, serializable payload for the event."""
    payload = {}
    if node_name == "supervisor":
        payload = {"parsed_intent": output.get("parsed_intent", {})}
    elif node_name == "design_agent":
        code = output.get("cad_code", "")
        payload = {"code_preview": code[:200] + "..." if len(code) > 200 else code}
    elif node_name == "geometry_validator":
        payload = {
            "valid": output.get("geometry_valid", False),
            "errors": output.get("validation_errors", []),
            "stats": output.get("validation_stats", {}),
        }
    elif node_name == "dfm_agent":
        r = output.get("dfm_report", {})
        payload = {"score": r.get("overall_score", 0), "issues": len(r.get("issues", []))}
    elif node_name == "cost_agent":
        c = output.get("cost_estimate", {})
        payload = {"unit_cost": c.get("total_unit_cost_usd", 0)}
    return payload


def _agent_message(node_name: str, output: dict) -> str:
    if node_name == "supervisor":
        return f"Parsed intent: {output.get('parsed_intent', {}).get('summary', '')}"
    elif node_name == "geometry_validator":
        valid = output.get("geometry_valid", False)
        return "Geometry valid ✓" if valid else f"Errors: {'; '.join(output.get('validation_errors', []))}"
    elif node_name == "dfm_agent":
        score = output.get("dfm_report", {}).get("overall_score", 0)
        return f"DFM score: {score}/100"
    elif node_name == "cost_agent":
        cost = output.get("cost_estimate", {}).get("total_unit_cost_usd", 0)
        return f"Estimated unit cost: ${cost:.2f}"
    return f"{AGENT_DISPLAY.get(node_name, node_name)} completed"
