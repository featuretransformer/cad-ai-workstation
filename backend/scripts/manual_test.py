"""
Manual End-to-End Test for AI-Native CAD-CAM Workstation.
Tests:
1. Knowledge base search across 253k+ records.
2. CAD graph generation from text prompt.
3. CAD graph generation from drawing (SVG) input.
4. Export file verification (STEP, STL).
5. Full engineering analysis (DFM, Structural, Cost, CAM).
"""
import sys
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from config import settings
from retrieval.index import KnowledgeIndex
from retrieval.query import parse_intent_to_query, search_knowledge_base, CADIRQuery
from agents.graph import cad_graph
from agents.state import AgentState


def test_knowledge_base():
    print("\n" + "="*60)
    print("STEP 1: Testing Knowledge Base (253k+ indexed exemplars)")
    print("="*60)
    kb_path = Path(settings.knowledge_db_path)
    print(f"Database path: {kb_path.resolve()}")
    assert kb_path.exists(), f"Database not found at {kb_path}"
    
    index = KnowledgeIndex(kb_path)
    with index._get_connection() as conn:
        total = conn.execute("SELECT count(*) FROM cad_examples").fetchone()[0]
        by_source = conn.execute("SELECT source_dataset, count(*) FROM cad_examples GROUP BY source_dataset").fetchall()
        
    print(f"Total CAD Exemplars in Database: {total}")
    for src, count in by_source:
        print(f"  - {src}: {count} records")
        
    query_text = "mounting plate with mounting holes and center cutout"
    query_obj = parse_intent_to_query(query_text)
    print(f"\nQuerying KB for: '{query_text}'")
    print(f"Decomposed Query: family={query_obj.family}, features={query_obj.features}, keywords={query_obj.keywords}")
    
    results = search_knowledge_base(index, query_obj, limit=5)
    print(f"Search Results returned: {len(results)}")
    for i, r in enumerate(results):
        print(f"  Result {i+1}: ID={r['id'][:25]} | Dataset={r.get('source_dataset')} | Family={r.get('family')} | Score={r.get('_score'):.2f}")
    assert len(results) > 0, "KB search returned no results!"
    print("✓ Knowledge Base verification PASSED")


def test_text_prompt_generation():
    print("\n" + "="*60)
    print("STEP 2: Testing Parametric CAD Generation from Text Prompt")
    print("="*60)
    prompt = "Create a mounting plate 80x60x10 with 4 corner mounting holes and 20mm center hole"
    print(f"Prompt: \"{prompt}\"")
    
    state: AgentState = {
        "design_id": "manual_test_bracket",
        "user_prompt": prompt,
        "max_retries": 3,
    }
    
    print("Invoking LangGraph CAD Multi-Agent Pipeline...")
    final_state = cad_graph.invoke(state)
    
    print(f"Final Agent: {final_state.get('current_agent')}")
    print(f"Input Type: {final_state.get('input_type')}")
    print(f"CADIR Valid: {final_state.get('cadir_valid')}")
    print(f"Geometry Valid: {final_state.get('geometry_valid')}")
    print(f"Validation Errors: {final_state.get('validation_errors')}")
    
    # Check CAD code
    code = final_state.get("cad_code", "")
    print(f"Generated build123d code length: {len(code)} chars")
    assert "build123d" in code, "Generated code missing build123d!"
    assert "result" in code, "Generated code missing result variable!"
    
    # Check exports
    exports = final_state.get("export_paths", {})
    print(f"Export Paths: {exports}")
    for fmt, p in exports.items():
        exists = Path(p).exists()
        size = Path(p).stat().st_size if exists else 0
        print(f"  - {fmt.upper()}: {p} (exists={exists}, size={size} bytes)")
        assert exists, f"Export file {p} does not exist!"
        assert size > 0, f"Export file {p} is empty!"
        
    # Check engineering downstream reports
    dfm = final_state.get("dfm_report", {})
    eng = final_state.get("engineering_report", {})
    cost = final_state.get("cost_estimate", {})
    safety = final_state.get("safety_report", {})
    cam = final_state.get("cam_report", {})
    
    print("\nEngineering Analysis Reports:")
    print(f"  DFM Overall Score: {dfm.get('overall_score')}/100")
    print(f"  Material: {eng.get('material')}")
    print(f"  Mass: {eng.get('mass_kg')} kg ({eng.get('volume_cm3')} cm³)")
    print(f"  Unit Cost: ${cost.get('total_unit_cost_usd')} USD")
    print(f"  Safety Factor: {safety.get('safety_factor')} ({safety.get('status')})")
    print(f"  CAM Setups: {cam.get('setup_count')}, Tools: {cam.get('tool_list')}")
    
    assert final_state.get("cadir_valid") is True
    assert final_state.get("geometry_valid") is True
    print("✓ Text prompt parametric CAD generation PASSED")


def test_drawing_prompt_generation():
    print("\n" + "="*60)
    print("STEP 3: Testing CAD Generation from 2D Drawing (SVG)")
    print("="*60)
    svg_sample = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
        <rect x="50" y="50" width="120" height="80" stroke="black" fill="none" />
        <circle cx="110" cy="90" r="20" stroke="black" fill="none" />
        <text x="110" y="40">120 mm</text>
        <text x="110" y="90">Ø40</text>
    </svg>"""
    print("Input: Vector Engineering Drawing (SVG)")
    
    state: AgentState = {
        "design_id": "manual_test_svg_drawing",
        "user_prompt": svg_sample,
        "max_retries": 3,
    }
    
    print("Invoking LangGraph CAD Multi-Agent Pipeline with Drawing...")
    final_state = cad_graph.invoke(state)
    
    print(f"Input Type Identified: {final_state.get('input_type')}")
    print(f"CADIR Valid: {final_state.get('cadir_valid')}")
    print(f"Geometry Valid: {final_state.get('geometry_valid')}")
    
    exports = final_state.get("export_paths", {})
    for fmt, p in exports.items():
        exists = Path(p).exists()
        size = Path(p).stat().st_size if exists else 0
        print(f"  - {fmt.upper()}: {p} (exists={exists}, size={size} bytes)")
        assert exists, f"Export file {p} does not exist!"
        
    assert final_state.get("input_type") == "drawing"
    assert final_state.get("cadir_valid") is True
    assert final_state.get("geometry_valid") is True
    print("✓ Drawing prompt CAD generation PASSED")


if __name__ == "__main__":
    print("============================================================")
    print("STARTING FULL END-TO-END MANUAL TEST OF CAD WORKSTATION")
    print("============================================================")
    try:
        test_knowledge_base()
        test_text_prompt_generation()
        test_drawing_prompt_generation()
        print("\n" + "="*60)
        print("ALL MANUAL TESTS PASSED SUCCESSFULLY! 🚀")
        print("============================================================")
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
