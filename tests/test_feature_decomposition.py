"""
Unit and Integration Tests for Complex Prompt Feature Decomposition Pipeline.
Validates:
- Complexity scoring and classifier gate logic
- Feature planner ordering rules (base body first, edge blends last)
- Incremental design agent step generation and merge logic
- End-to-end LangGraph execution on complex prompts
"""
import pytest
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.complexity_classifier import evaluate_prompt_complexity, complexity_classifier_node
from agents.feature_planner import (
    decompose_complex_prompt_deterministic,
    plan_features_with_llm,
    feature_planner_node,
)
from agents.incremental_design_agent import (
    merge_step_features,
    _synthesize_step_features_deterministic,
    incremental_design_agent_node,
)
from cad.cadir.schema import CADIRDocument, CADIRFeature, Point3D
from cad.cadir.validator import validate_cadir_document
from cad.cadir.interpreter import generate_build123d_code
from agents.graph import cad_graph


class TestComplexityClassifier:
    """Validates complexity scoring and routing gate."""

    def test_simple_prompts_classified_as_simple(self):
        simple_prompts = [
            "M10 hex nut with 1.5mm pitch",
            "Washer with OD 30mm, ID 10mm, thickness 3mm",
            "Simple stepped shaft diameter 20mm and 15mm",
            "Aluminium spacer tube 25mm long",
        ]
        for p in simple_prompts:
            res = evaluate_prompt_complexity(p)
            assert not res["is_complex"], f"Prompt '{p}' should be classified as simple, got score {res['complexity_score']}"

    def test_complex_prompts_classified_as_complex(self):
        complex_prompts = [
            "Motor housing with cooling fins, cable routing channels, bearing bore with snap-ring groove, and M6 mounting flanges",
            "Hydraulic manifold block with 3 parallel 10mm channels connected by cross-ports and M8 tapped holes",
            "Gearbox housing 120x80x60 with internal pocket, opposing bearing bores, oil drain boss, and lifting lug",
            "Flanged bearing housing with 35mm bore, 4x M8 mounting holes on 80mm PCD, and 2mm fillets on all edges",
        ]
        for p in complex_prompts:
            res = evaluate_prompt_complexity(p)
            assert res["is_complex"], f"Prompt '{p}' should be classified as complex, got score {res['complexity_score']}"
            assert res["complexity_score"] >= 4.0

    def test_complexity_classifier_node(self):
        state = {
            "user_prompt": "Motor housing with cooling fins, cable routing channels, and mounting flange",
            "is_assembly": False,
        }
        out = complexity_classifier_node(state)
        assert out["is_complex_part"] is True
        assert out["complexity_score"] >= 4.0


class TestFeaturePlanner:
    """Validates Feature Build Plan construction and mechanical ordering."""

    def test_deterministic_plan_structure(self):
        prompt = "Motor housing with cooling fins, cable gland boss, bearing bore with snap-ring groove, and mounting flange"
        plan = decompose_complex_prompt_deterministic(prompt, {"dimensions": [80, 120]})

        assert len(plan) >= 3, f"Expected at least 3 steps, got {len(plan)}"
        
        # Step 1 must be base body
        assert plan[0]["step"] == 1
        assert "body" in plan[0]["group_name"].lower() or "cylinder" in plan[0]["group_name"].lower()
        assert plan[0]["depends_on_steps"] == []

        # Intermediate steps must depend on Step 1
        for s in plan[1:]:
            assert 1 in s["depends_on_steps"] or len(s["depends_on_steps"]) > 0

        # Last step should be edge finishing / fillets if requested or detail
        last_step = plan[-1]
        assert "fillet" in str(last_step["feature_types"]) or "chamfer" in str(last_step["feature_types"]) or "edge" in last_step["group_name"].lower()

    def test_box_manifold_plan(self):
        prompt = "Manifold block 100x80x50 with internal pocket, 3 fluid channels, and mounting holes with edge fillets"
        plan = decompose_complex_prompt_deterministic(prompt, {})
        assert len(plan) >= 3
        assert "box" in plan[0]["feature_types"]


class TestIncrementalMergeLogic:
    """Validates step feature synthesis and safe topological merging."""

    def test_merge_step_features_rerooting(self):
        doc = CADIRDocument(
            id="doc_test",
            name="Test Part",
            component_family="housing",
            units="mm",
            features=[
                CADIRFeature(
                    id="base_cyl",
                    name="Base Body",
                    feature_type="cylinder",
                    radius=40.0,
                    height=100.0,
                    operation="new_body",
                    dependencies=[],
                )
            ]
        )

        # Step 2: Add bore (which LLM might emit as new_body by accident)
        new_feats = [
            CADIRFeature(
                id="central_bore",
                name="Central Bore",
                feature_type="hole",
                radius=15.0,
                diameter=30.0,
                depth=120.0,
                operation="new_body",  # Should be normalized to 'cut'
                dependencies=[],
            )
        ]

        merged = merge_step_features(doc, new_feats, step_number=2)
        assert len(merged.features) == 2
        
        bore_f = merged.features[1]
        assert bore_f.operation == "cut"
        assert "base_cyl" in bore_f.dependencies
        assert bore_f.id.startswith("s2_")

    def test_merge_clamps_oversized_features(self):
        doc = CADIRDocument(
            id="doc_test",
            name="Test Part",
            component_family="housing",
            units="mm",
            features=[
                CADIRFeature(
                    id="base_cyl",
                    name="Base Body",
                    feature_type="cylinder",
                    radius=30.0,
                    height=80.0,
                    operation="new_body",
                    dependencies=[],
                )
            ]
        )

        # Oversized hole (radius 40mm inside 30mm cylinder)
        oversized_hole = [
            CADIRFeature(
                id="huge_hole",
                name="Oversized Hole",
                feature_type="hole",
                radius=45.0,
                diameter=90.0,
                depth=100.0,
                operation="cut",
                dependencies=[],
            )
        ]

        merged = merge_step_features(doc, oversized_hole, step_number=2)
        hole_f = merged.features[1]
        assert hole_f.radius < 30.0, f"Hole radius should be clamped to fit host body, got {hole_f.radius}"

    def test_merge_deduplicates_edge_modifications(self):
        doc = CADIRDocument(
            id="doc_test",
            name="Test Part",
            component_family="housing",
            units="mm",
            features=[
                CADIRFeature(
                    id="base_cyl",
                    name="Base Body",
                    feature_type="cylinder",
                    radius=30.0,
                    height=80.0,
                    operation="new_body",
                    dependencies=[],
                ),
                CADIRFeature(
                    id="fillet_1",
                    name="Vertical Fillet",
                    feature_type="fillet",
                    radius=2.0,
                    edge_selector="vertical",
                    operation="join",
                    dependencies=["base_cyl"],
                )
            ]
        )

        # Second step tries to add duplicate fillet on vertical edges
        duplicate_fillet = [
            CADIRFeature(
                id="fillet_dup",
                name="Duplicate Vertical Fillet",
                feature_type="fillet",
                radius=2.0,
                edge_selector="vertical",
                operation="join",
                dependencies=[],
            )
        ]

        merged = merge_step_features(doc, duplicate_fillet, step_number=3)
        # Should NOT have added a duplicate vertical fillet
        fillet_count = sum(1 for f in merged.features if f.feature_type == "fillet" and f.edge_selector == "vertical")
        assert fillet_count == 1


class TestEndToEndDecompositionWorkflow:
    """Validates complete LangGraph execution through the decomposition branch."""

    def test_complex_motor_housing_execution(self):
        prompt = "Motor housing with cooling fins, bearing bore with snap-ring groove, and M6 mounting flanges"
        
        initial_state = {
            "design_id": "test_decomp_001",
            "session_id": "session_test",
            "user_prompt": prompt,
            "parsed_intent": {"dimensions": [80, 120]},
            "max_retries": 2,
            "is_assembly": False,
        }

        # Run through workflow
        final_state = dict(initial_state)
        for event in cad_graph.stream(initial_state, config={"recursion_limit": 50}, stream_mode="updates"):
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    final_state.update(node_output)

        assert final_state.get("is_complex_part") is True
        assert final_state.get("decomposition_used") is True
        
        # Verify CADIR document was generated with multiple features
        cadir = final_state.get("cadir_document")
        assert cadir is not None
        assert len(cadir.features) >= 3, f"Expected >= 3 features in decomposed CADIR, got {len(cadir.features)}"

        # Verify geometry valid and export paths produced
        assert final_state.get("geometry_valid") is True, f"Geometry validation failed: {final_state.get('validation_errors')}"
        assert "step" in final_state.get("export_paths", {})
        assert "stl" in final_state.get("export_paths", {})
        assert "glb" in final_state.get("export_paths", {})
