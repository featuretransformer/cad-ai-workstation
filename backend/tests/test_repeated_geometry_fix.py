"""
Regression tests for the repeated geometry bug fix.

Validates that:
1. Different prompts produce different geometries
2. Identical prompts produce consistent geometries
3. Dimensions are correctly extracted and applied
4. Hash-based fallback produces deterministic but unique results
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.design_agent import (
    _synthesize_parametric_cadir,
    _classify_component_family,
    _extract_dimensions_robust,
    _generate_unique_dimensions,
)


class TestComponentClassification:
    """Test improved component family classification."""
    
    def test_washer_classification(self):
        assert _classify_component_family("create a washer", {}) == "washer"
        assert _classify_component_family("flat washer 30mm", {}) == "washer"
        assert _classify_component_family("spring washer", {}) == "washer"
    
    def test_nut_classification(self):
        assert _classify_component_family("hex nut", {}) == "nut"
        assert _classify_component_family("create a nut", {}) == "nut"
        assert _classify_component_family("M6 hexnut", {}) == "nut"
    
    def test_bracket_classification(self):
        assert _classify_component_family("mounting bracket", {}) == "bracket"
        assert _classify_component_family("L-bracket", {}) == "bracket"
        assert _classify_component_family("angle bracket", {}) == "bracket"
    
    def test_shaft_classification(self):
        assert _classify_component_family("create a shaft", {}) == "shaft"
        assert _classify_component_family("cylindrical rod", {}) == "shaft"
        assert _classify_component_family("axle", {}) == "shaft"
    
    def test_plate_classification(self):
        assert _classify_component_family("mounting plate", {}) == "plate"
        assert _classify_component_family("base plate", {}) == "plate"
        assert _classify_component_family("flat plate", {}) == "plate"
    
    def test_intent_override(self):
        intent = {"component_family": "gear"}
        assert _classify_component_family("create something", intent) == "gear"
    
    def test_unknown_defaults_to_custom(self):
        assert _classify_component_family("something weird", {}) == "custom_part"


class TestDimensionExtraction:
    """Test robust dimension extraction."""
    
    def test_extract_with_mm_units(self):
        dims = _extract_dimensions_robust("create a 50mm x 30mm x 10mm box", {})
        assert 50.0 in dims
        assert 30.0 in dims
        assert 10.0 in dims
    
    def test_extract_without_units(self):
        dims = _extract_dimensions_robust("create a box 100 by 75 by 20", {})
        assert 100.0 in dims
        assert 75.0 in dims
        assert 20.0 in dims
    
    def test_extract_with_labels(self):
        dims = _extract_dimensions_robust("length: 60mm, width: 40mm, height: 12mm", {})
        assert 60.0 in dims
        assert 40.0 in dims
        assert 12.0 in dims
    
    def test_extract_diameter(self):
        dims = _extract_dimensions_robust("washer diameter 30mm", {})
        assert 30.0 in dims
    
    def test_intent_dimensions_priority(self):
        intent = {"dimensions": [25.0, 15.0, 5.0]}
        dims = _extract_dimensions_robust("create a 100mm thing", intent)
        # Intent dimensions have priority
        assert dims == [25.0, 15.0, 5.0]
    
    def test_no_dimensions_returns_empty(self):
        dims = _extract_dimensions_robust("create something cool", {})
        assert dims == []
    
    def test_removes_duplicates(self):
        dims = _extract_dimensions_robust("50mm by 50mm by 30mm", {})
        # Should have 50 only once
        assert dims.count(50.0) == 1
        assert 30.0 in dims


class TestUniqueHashedDimensions:
    """Test that prompt hash generates unique but deterministic dimensions."""
    
    def test_different_prompts_different_dimensions(self):
        dims1 = _generate_unique_dimensions("create a simple plate", [60, 40, 12], 3)
        dims2 = _generate_unique_dimensions("make a mounting bracket", [60, 40, 12], 3)
        
        # Dimensions should be different
        assert dims1 != dims2
        print(f"Prompt 1 dims: {dims1}")
        print(f"Prompt 2 dims: {dims2}")
    
    def test_same_prompt_same_dimensions(self):
        dims1 = _generate_unique_dimensions("create a test part", [50, 35, 8], 3)
        dims2 = _generate_unique_dimensions("create a test part", [50, 35, 8], 3)
        
        # Identical prompts should produce identical dimensions
        assert dims1 == dims2
    
    def test_dimensions_in_reasonable_range(self):
        dims = _generate_unique_dimensions("test prompt", [100, 80, 20], 3)
        
        # With 0.5-1.5x variation, dims should be between 50-150, 40-120, 10-30
        assert 50 <= dims[0] <= 150
        assert 40 <= dims[1] <= 120
        assert 10 <= dims[2] <= 30
    
    def test_generates_requested_count(self):
        dims = _generate_unique_dimensions("test", [10, 20, 30, 40], 5)
        assert len(dims) == 5


class TestRepeatedGeometryFix:
    """
    Critical regression tests for the repeated geometry bug.
    
    These tests validate that different prompts produce genuinely different
    CADIR documents and geometry specifications.
    """
    
    def test_different_prompts_different_cadir_documents(self):
        """Different prompts must produce different CADIR documents."""
        
        prompt1 = "create a simple mounting plate"
        prompt2 = "make a sturdy bracket for mounting"
        
        doc1 = _synthesize_parametric_cadir("test_id_1", prompt1, {}, [])
        doc2 = _synthesize_parametric_cadir("test_id_2", prompt2, {}, [])
        
        # Should classify to different families
        assert doc1.component_family != doc2.component_family
        print(f"Doc1 family: {doc1.component_family}, Doc2 family: {doc2.component_family}")
        
        # Should have different feature counts or dimensions
        assert (doc1.features[0].length != doc2.features[0].length or
                doc1.features[0].width != doc2.features[0].width or
                doc1.features[0].height != doc2.features[0].height)
    
    def test_identical_prompts_identical_cadir(self):
        """Identical prompts should produce consistent results."""
        
        prompt = "create a washer with 30mm outer diameter"
        
        doc1 = _synthesize_parametric_cadir("test_a", prompt, {}, [])
        doc2 = _synthesize_parametric_cadir("test_b", prompt, {}, [])
        
        # Same family
        assert doc1.component_family == doc2.component_family
        
        # Same feature types
        assert len(doc1.features) == len(doc2.features)
        
        # For washer with explicit dimension, should use 30mm
        # Note: The design_id makes doc.id different, but geometry should match
        assert doc1.features[0].distance == doc2.features[0].distance
    
    def test_extracted_dimensions_applied(self):
        """Verify that extracted dimensions are actually used in geometry."""
        
        prompt = "create a 50mm x 30mm x 15mm rectangular box"
        intent = {}
        
        doc = _synthesize_parametric_cadir("test_dims", prompt, intent, [])
        
        # Should extract and apply these dimensions
        dims_in_prompt = [50.0, 30.0, 15.0]
        
        # Check first feature uses these dimensions
        f = doc.features[0]
        assert f.length in dims_in_prompt
        assert f.width in dims_in_prompt
        assert f.height in dims_in_prompt
    
    def test_no_dimensions_uses_unique_hash(self):
        """When no dimensions are extracted, hash-based generation is used."""
        
        prompt1 = "create something cool"
        prompt2 = "make a random part"
        
        doc1 = _synthesize_parametric_cadir("hash_test_1", prompt1, {}, [])
        doc2 = _synthesize_parametric_cadir("hash_test_2", prompt2, {}, [])
        
        # Different prompts -> different dimensions
        f1 = doc1.features[0]
        f2 = doc2.features[0]
        
        # At least one dimension should differ
        assert (f1.length != f2.length or
                f1.width != f2.width or
                f1.height != f2.height)
        
        print(f"Prompt1 dims: L={f1.length}, W={f1.width}, H={f1.height}")
        print(f"Prompt2 dims: L={f2.length}, W={f2.width}, H={f2.height}")
    
    def test_engineering_intent_documents_extraction(self):
        """Verify engineering_intent field documents dimension extraction."""
        
        prompt_with_dims = "50mm washer"
        doc1 = _synthesize_parametric_cadir("intent_1", prompt_with_dims, {}, [])
        
        assert "extracted_dimensions" in doc1.engineering_intent
        assert doc1.engineering_intent["extracted_dimensions"]  # Non-empty
        
        prompt_no_dims = "create something"
        doc2 = _synthesize_parametric_cadir("intent_2", prompt_no_dims, {}, [])
        
        # Should have warning when no dimensions extracted
        assert "warning" in doc2.engineering_intent or \
               doc2.engineering_intent.get("extracted_dimensions") == []


class TestGeometryConsistency:
    """Test that generated geometry is geometrically valid."""
    
    def test_positive_dimensions(self):
        """All generated dimensions must be positive."""
        
        doc = _synthesize_parametric_cadir("pos_test", "create a part", {}, [])
        
        for feature in doc.features:
            if hasattr(feature, "length") and feature.length is not None:
                assert feature.length > 0
            if hasattr(feature, "width") and feature.width is not None:
                assert feature.width > 0
            if hasattr(feature, "height") and feature.height is not None:
                assert feature.height > 0
            if hasattr(feature, "diameter") and feature.diameter is not None:
                assert feature.diameter > 0
            if hasattr(feature, "radius") and feature.radius is not None:
                assert feature.radius > 0
    
    def test_feature_dependencies_valid(self):
        """Feature dependencies should reference existing features."""
        
        doc = _synthesize_parametric_cadir("dep_test", "create a bracket", {}, [])
        
        feature_ids = {f.id for f in doc.features}
        
        for feature in doc.features:
            for dep_id in feature.dependencies:
                assert dep_id in feature_ids, f"Dependency {dep_id} not found in feature list"


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
