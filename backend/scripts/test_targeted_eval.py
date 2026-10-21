import sys
import json
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from agents.graph import cad_graph
from agents.state import AgentState

prompts_file = backend_dir / "scripts" / "parsed_user_prompts.json"
with open(prompts_file, "r", encoding="utf-8") as f:
    prompts = json.load(f)

test_ids = ["E06", "E08", "E10", "E14", "E17", "E19", "E20", "M04", "C05", "C12"]
test_prompts = [p for p in prompts if p["id"] in test_ids]

for item in test_prompts:
    pid = item["id"]
    name = item["name"]
    prompt = item["prompt"]
    print(f"=== Testing {pid}: {name} ===")
    t0 = time.time()
    state: AgentState = {
        "design_id": f"test_reeval_{pid.lower()}",
        "session_id": "sess_test",
        "user_prompt": prompt,
        "max_retries": 2,
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
        "last_error": "",
        "messages": [],
    }
    res = cad_graph.invoke(state)
    dt = round(time.time() - t0, 2)
    is_asm = res.get("is_assembly", False)
    cadir_v = res.get("cadir_valid", False)
    geom_v = res.get("geometry_valid", False)
    exec_res = res.get("execution_result", {})
    vol = exec_res.get("volume", 0.0)
    bbox = exec_res.get("bounding_box", {})
    asm_spec = res.get("assembly_spec", {})
    comps = 0
    if is_asm and asm_spec:
        if hasattr(asm_spec, "components"):
            comps = len(asm_spec.components)
            comp_names = [c.name for c in asm_spec.components]
        elif isinstance(asm_spec, dict):
            comps = len(asm_spec.get("components", []))
            comp_names = [c.get("name") for c in asm_spec.get("components", [])]
        print(f"Assembly components ({comps}): {comp_names}")
    
    print(f"Result: is_asm={is_asm}, comps={comps}, cadir_v={cadir_v}, geom_v={geom_v}, vol={round(vol, 1)} mm3, bbox={bbox}, time={dt}s")
    err = res.get("last_error")
    if err:
        print(f"  Note/Error: {err}")
    print()
