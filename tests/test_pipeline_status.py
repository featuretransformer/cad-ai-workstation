"""Regression tests for durable pipeline failure semantics."""
import sys
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))

from tasks.cad_tasks import run_cad_pipeline


def test_invalid_geometry_is_not_marked_complete():
    class FakeDB:
        def rollback(self): pass
        def close(self): pass
    updates = []
    class FakeCrud:
        def update_design(self, db, design_id, **kwargs): updates.append(kwargs); return object()
        def create_agent_log(self, *args, **kwargs): return object()
        def create_export(self, *args, **kwargs): return object()
    class FakeGraph:
        def stream(self, *args, **kwargs):
            yield {"geometry_validator": {"geometry_valid": False, "validation_errors": ["Mesh is empty"], "validation_stats": {}, "last_error": ""}}
    with patch("tasks.cad_tasks.SessionLocal", return_value=FakeDB()), patch("tasks.cad_tasks.crud", FakeCrud()), patch("tasks.cad_tasks.cad_graph", FakeGraph()), patch("tasks.cad_tasks.redis.from_url", side_effect=Exception("offline")):
        result = run_cad_pipeline.run("design-1", "make a part")
    assert result["status"] == "failed"
    assert any(update.get("status") == "FAILED" and update.get("failure_reason") == "Mesh is empty" for update in updates)
