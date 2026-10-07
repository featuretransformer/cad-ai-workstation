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
    "input_classifier": "Input Classifier",
    "supervisor": "Supervisor",
    "design_agent": "Design Agent",
    "cadir_validator": "CADIR Validator",
    "interpreter": "CADIR Interpreter",
    "cad_executor": "CAD Executor",
    "geometry_validator": "Geometry Validator",
    "cadir_repair": "CADIR Repair Agent",
    "dfm_agent": "DFM Analyst",
    "engineering_agent": "Engineering Agent",
    "cost_agent": "Cost Estimator",
    "safety_agent": "Safety Agent",
    "alternatives_agent": "Alternatives Agent",
    "cam_agent": "CAM Agent",
    "doc_agent": "Documentation Agent",
}


def publish_event(r, design_id: str, event: dict):
    """Publish an event to the design's Redis channel (no-op if Redis is unavailable)."""
    if r is None:
        return
    try:
        channel = f"design:{design_id}:events"
        r.publish(channel, json.dumps(event))
    except Exception:
        pass


@celery_app.task(
    bind=True,
    name="tasks.cad_tasks.run_cad_pipeline",
    max_retries=0
)
def run_cad_pipeline(self: Task, design_id: str, prompt: str):

    # Redis is optional — if unavailable, pipeline still runs but no real-time WS events
    r = None
    try:
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
    except Exception as re:
        print(f"Redis unavailable ({re}), running without real-time events")
        r = None

    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # 1. Mark design as IN_PROGRESS
        # ---------------------------------------------------------
        try:
            crud.update_design(
                db,
                design_id,
                status="IN_PROGRESS"
            )
        except Exception as e:
            print(f"Could not update status to IN_PROGRESS: {e}")

        publish_event(
            r,
            design_id,
            {
                "type": "pipeline_started",
                "design_id": design_id,
                "status": "IN_PROGRESS",
                "message": "Starting AI-native CAD pipeline..."
            }
        )

        # ---------------------------------------------------------
        # 2. Initial LangGraph state
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 3. Execute LangGraph ONCE
        # ---------------------------------------------------------
        final_state = dict(initial_state)

        for event in cad_graph.stream(
            initial_state,
            stream_mode="updates"
        ):

            for node_name, node_output in event.items():

                # Merge node output into final state
                if isinstance(node_output, dict):
                    final_state.update(node_output)

                display_name = AGENT_DISPLAY.get(
                    node_name,
                    node_name
                )

                confidence = (
                    node_output
                    .get("confidence_scores", {})
                    .get(node_name, 0)
                )

                payload = _safe_payload(
                    node_name,
                    node_output
                )

                # -------------------------------------------------
                # Redis event
                # -------------------------------------------------
                publish_event(
                    r,
                    design_id,
                    {
                        "type": "agent_update",
                        "design_id": design_id,
                        "agent": node_name,
                        "display_name": display_name,
                        "status": "done",
                        "confidence": confidence,
                        "payload": payload,
                    }
                )

                # -------------------------------------------------
                # DB agent log
                # -------------------------------------------------
                try:
                    crud.create_agent_log(
                        db,
                        design_id,
                        node_name,
                        "done",
                        message=_agent_message(
                            node_name,
                            node_output
                        ),
                        confidence=confidence,
                        payload=payload,
                    )
                except Exception as e:
                    print(
                        f"Agent log error "
                        f"({node_name}): {e}"
                    )

        # ---------------------------------------------------------
        # 4. Save final design state
        # ---------------------------------------------------------
        update_data = {}

        if final_state.get("cad_code"):
            update_data["cad_code"] = final_state["cad_code"]

        if final_state.get("feature_tree"):
            update_data["feature_tree"] = final_state["feature_tree"]

        update_data["geometry_valid"] = final_state.get(
            "geometry_valid",
            False
        )

        for field in [
            "dfm_report",
            "engineering_report",
            "cost_estimate",
            "safety_report",
            "alternatives",
            "confidence_scores",
        ]:
            if final_state.get(field):
                update_data[field] = final_state[field]

        # ---------------------------------------------------------
        # 5. Save export files
        # ---------------------------------------------------------
        for fmt, path in final_state.get(
            "export_paths",
            {}
        ).items():

            try:
                size = get_file_size(path)

                crud.create_export(
                    db,
                    design_id,
                    fmt,
                    path,
                    size
                )

            except Exception as e:
                print(
                    f"Export save error "
                    f"({fmt}): {e}"
                )

        # ---------------------------------------------------------
        # 6. Mark COMPLETE
        # ---------------------------------------------------------
        update_data["status"] = "COMPLETE"

        crud.update_design(
            db,
            design_id,
            **update_data
        )

        # ---------------------------------------------------------
        # 7. Final Redis event
        # ---------------------------------------------------------
        publish_event(
            r,
            design_id,
            {
                "type": "pipeline_complete",
                "design_id": design_id,
                "status": "COMPLETE",
                "geometry_valid": final_state.get(
                    "geometry_valid",
                    False
                ),
                "export_paths": final_state.get(
                    "export_paths",
                    {}
                ),
                "confidence_scores": final_state.get(
                    "confidence_scores",
                    {}
                ),
                "message": (
                    "Pipeline complete!"
                    if final_state.get("geometry_valid")
                    else
                    "Pipeline completed but geometry "
                    "is invalid."
                ),
            }
        )

        return {
            "status": "complete",
            "design_id": design_id,
            "geometry_valid": final_state.get(
                "geometry_valid",
                False
            ),
        }

    except Exception as e:

        # ---------------------------------------------------------
        # Mark FAILED
        # ---------------------------------------------------------
        try:
            crud.update_design(
                db,
                design_id,
                status="FAILED"
            )
        except Exception as db_error:
            print(
                f"Could not mark design FAILED: "
                f"{db_error}"
            )

        # ---------------------------------------------------------
        # Publish error
        # ---------------------------------------------------------
        publish_event(
            r,
            design_id,
            {
                "type": "pipeline_error",
                "design_id": design_id,
                "status": "FAILED",
                "error": str(e),
            }
        )

        raise

    finally:
        db.close()
        if r is not None:
            try:
                r.close()
            except Exception:
                pass





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
