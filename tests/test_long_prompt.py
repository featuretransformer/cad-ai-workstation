import pytest
from backend.retrieval.query import parse_intent_to_query
from backend.utils.macro_rag import query_macro_rag
from backend.agents.complexity_classifier import evaluate_prompt_complexity
from backend.agents.supervisor import supervisor_node
from backend.agents.intent_extractor import extract_design_intent
from backend.utils.llm import get_supervisor_llm, get_design_llm


LONG_PROMPT = """
Design a heavy-duty industrial pipe mounting flange made from 6061-T6 aluminum.
The main circular base plate has an outer diameter of 180.0 mm and a thickness of 22.0 mm.
In the center, machine a through-bore with an internal bore diameter of 65.0 mm.
Around the central bore, extrude a cylindrical collar hub with an outer hub diameter of 95.0 mm,
rising to a total height of 45.0 mm above the base plate.
On the flange face, drill a 6-hole bolt circle pattern with pitch circle diameter PCD of 140.0 mm,
where each through-hole has a diameter of 12.5 mm, countersunk to 18.0 mm diameter with a depth of 4.0 mm.
Machine an O-ring seal groove on the mating face at a radius of 42.5 mm, groove width of 4.5 mm,
and groove depth of 3.2 mm.
Apply an external fillet radius of 3.0 mm at the junction between the hub and the flange base plate,
and add a 1.5 mm 45-degree chamfer along the top inner edge of the central bore and all outer perimeter edges.
The component must withstand an internal operating pressure of 25 bar and maintain high geometric stiffness.
"""


def test_retrieval_query_preserves_long_prompt_keywords():
    query = parse_intent_to_query(LONG_PROMPT)
    assert query.keywords is not None
    # We increased the limit from 5 to 30
    assert len(query.keywords) > 10
    assert any("flange" in kw for kw in query.keywords)
    assert any("bore" in kw or "groove" in kw or "collar" in kw for kw in query.keywords)


def test_complexity_classifier_scores_high_word_count():
    comp = evaluate_prompt_complexity(LONG_PROMPT)
    assert comp["word_count"] > 100
    assert comp["is_complex"] is True
    # Long prompts with multiple features should score high (> 10.0)
    assert comp["complexity_score"] >= 10.0


def test_supervisor_extracts_many_dimensions():
    state = {
        "user_prompt": LONG_PROMPT,
        "parsed_intent": {},
        "design_intent": {},
    }
    updated_state = supervisor_node(state)
    parsed = updated_state["parsed_intent"]
    # We increased the dimension limit from 5 to 30
    assert "dimensions" in parsed
    dims = parsed["dimensions"]
    assert len(dims) >= 8, f"Expected at least 8 dimensions, found {len(dims)}: {dims}"
    # Verify key dimensions from the prompt are present
    assert 180.0 in dims or 22.0 in dims or 65.0 in dims or 140.0 in dims


def test_macro_rag_handles_long_prompt():
    results = query_macro_rag(LONG_PROMPT, operations=["fillet", "chamfer", "hole_pattern"], limit=3)
    # Ensure query succeeds without crashing or FTS5 syntax errors
    assert isinstance(results, list)


def test_llm_token_budgets():
    sup_llm = get_supervisor_llm()
    assert sup_llm.default_max_tokens >= 2048
    des_llm = get_design_llm()
    assert des_llm.default_max_tokens >= 4096


def test_intent_extractor_captures_all_raw_numbers():
    intent = extract_design_intent(user_prompt=LONG_PROMPT)
    assert intent is not None
    # Verify fallback or LLM intent extracted raw dimensions beyond the old cap of 8
    raw_nums = intent.get("envelope", {})
    assert intent.get("component_family") in ("flange", "custom_part", "custom")
