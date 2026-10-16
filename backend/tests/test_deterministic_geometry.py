"""
Regression tests for deterministic CAD geometry generation bug fix.

CRITICAL BUG: Different prompts were generating identical geometry due to:
- Hardcoded fallback dimensions
- Missing dimension extraction from prompt text
- No unique seeding based on prompt content

These tests verify the fix ensures:
1. Different prompts produce different geometries
2. Identical prompts produce consistent results
3. Explicit dimensions are respected
4. Hash-based seeding creates variation
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from agents.design_agent import (
    _synthesize_parametric_cadir,
    extract_dimensions_from_text,
    get_prompt_seed,
)
from cad.cadir.schema import CADIRDocument


class TestDimensionExtraction:
    """Test dimension extraction from natural language prompts."""
    
    def test_extract_mm_dimensions(self):
        """Extract dimensions with mm units."""
        text = "Create a plate 100mm by 50mm with 5mm thickness"
        dims = extract_dimensions_from_text(text)
        assert 100.0 in dims
        assert 50.0 in dims
        assert 5.0 in dims
    
    def test_extract_cm_dimensions(self):
        """Extract and convert cm to mm."""
        text = "Make a box 10cm x 5cm x 3cm"
        dims = extract_dimensions_from_text(text)
        assert 100.0 in dims  # 10cm = 100mm
        assert 50.0 in dims   # 5cm = 50mm
        assert 30.0 in dims   # 3cm = 30mm
    
    def test_extract_dimension_keywords(self):
        """Extract dimensions from keyword patterns."""
        text = "diameter: 20, length: 50, width 30, thickness=5"
        dims = extract_dimensions_from_text(text)
        assert 20.0 in dims
        assert 50.0 in dims
        assert 30.0 in dims
        assert 5.0 in dims
    
    def test_no_duplicate_dimensions(self):
        """Ensure duplicates are removed."""
        text = "20mm by 20mm square with 20mm hole"
        dims = extract_dimensions_from_text(text)
        # Should only have one 20.0, not three
        assert dims.count(20.0) == 1
    
    def test_empty_when_no_dimensions(self):
        """Return empty list when no dimensions found."""
        text = "Create a simple part"
        dims = extract_dimensions_from_text(text)
        assert len(dims) == 0


class TestPromptSeeding:
    """Test deterministic seed generation from prompts."""
    
    def test_same_prompt_same_seed(self):
        """Identical prompts produce identical seeds."""
        prompt = "Create a mounting bracket"
        seed1 = get_prompt_seed(prompt)
        seed2 = get_prompt_seed(prompt)
        assert seed1 == seed2
    
    def test_different_prompts_different_seeds(self):
        """Different prompts produce different seeds."""
        prompt1 = "Create a mounting bracket"
        prompt2 = "Create a washer"
        prompt3 = "Create a hex nut"
        
        seed1 = get_prompt_seed(prompt1)
        seed2 = get_prompt_seed(prompt2)
        seed3 = get_prompt_seed(prompt3)
        
        assert seed1 != seed2
        assert seed2 != seed3
        assert seed1 != seed3
    
    def test_case_insensitive_seeding(self):
        """Case variations produce same seed."""
        seed1 = get_prompt_seed("Create a BRACKET")
        seed2 = get_prompt_seed("create a bracket")
        seed3 = get_prompt_seed("CREATE A BRACKET")
        
        assert seed1 == seed2
        assert seed2 == seed3
    
    def test_whitespace_normalized(self):
        """Whitespace variations produce same seed."""
        seed1 = get_prompt_seed("create a bracket")
        seed2 = get_prompt_seed("  create   a   bracket  ")
        
        assert seed1 == seed2


class TestDeterministicGeometry:
    """Test that different prompts produce different geometries."""
    
    def test_different_prompts_different_dimensions(self):
        """Different prompts produce different default dimensions."""
        prompt1 = "Create a simple washer"
        prompt2 = "Create a mounting bracket"
        prompt3 = "Create a hex nut"
        
        doc1 = _synthesize_parametric_cadir("test1", prompt1, {}, [])
        doc2 = _synthesize_parametric_cadir("test2", prompt2, {}, [])
        doc3 = _synthesize_parametric_cadir("test3", prompt3, {}, [])
        
        # Extract first feature dimensions for comparison
        def get_feature_dims(doc):
            if doc.features:
                f = doc.features[0]
                return (
                    getattr(f, 'length', None),
                    getattr(f, 'width', None),
                    getattr(f, 'height', None),
                    getattr(f, 'radius', None),
                    getattr(f, 'diameter', None),
                    getattr(f, 'distance', None),
                )
            return None
        
        dims1 = get_feature_dims(doc1)
        dims2 = get_feature_dims(doc2)
        dims3 = get_feature_dims(doc3)
        
        # At least one dimension should differ between each pair
        assert dims1 != dims2, "Washer and bracket should have different dimensions"
        assert dims2 != dims3, "Bracket and nut should have different dimensions"
        assert dims1 != dims3, "Washer and nut should have different dimensions"
    
    def test_identical_prompts_identical_geometry(self):
        """Identical prompts produce identical geometry."""
        prompt = "Create a mounting plate 60mm x 40mm"
        
        doc1 = _synthesize_parametric_cadir("test1", prompt, {}, [])
        doc2 = _synthesize_parametric_cadir("test2", prompt, {}, [])
        
        # Feature counts should match
        assert len(doc1.features) == len(doc2.features)
        
        # First feature should have same type
        assert doc1.features[0].feature_type == doc2.features[0].feature_type
        
        # Dimensions should match
        f1 = doc1.features[0]
        f2 = doc2.features[0]
        
        if hasattr(f1, 'length'):
            assert f1.length == f2.length
        if hasattr(f1, 'width'):
            assert f1.width == f2.width
        if hasattr(f1, 'height'):
            assert f1.height == f2.height
    
    def test_explicit_dimensions_respected(self):
        """Explicit dimensions from intent override defaults."""
        prompt = "Create a plate"
        intent = {
            "dimensions": [100.0, 80.0, 10.0],
            "component_family": "plate"
        }
        
        doc = _synthesize_parametric_cadir("test", prompt, intent, [])
        
        # First feature should use explicit dimensions
        assert doc.features[0].length == 100.0
        assert doc.features[0].width == 80.0
        assert doc.features[0].height == 10.0
    
    def test_extracted_dimensions_used(self):
        """Dimensions extracted from prompt text are used."""
        prompt = "Create a mounting plate 75mm by 45mm with 8mm thickness"
        intent = {}  # No explicit dimensions
        
        doc = _synthesize_parametric_cadir("test", prompt, intent, [])
        
        # Should use extracted dimensions
        f = doc.features[0]
        assert f.length == 75.0
        assert f.width == 45.0
        assert f.height == 8.0


class TestComponentClassification:
    """Test that different component types are correctly identified."""
    
    def test_washer_classification(self):
        """Washer keywords trigger washer geometry."""
        prompts = [
            "Create a washer",
            "Make a ring",
            "Design an annulus"
        ]
        
        for prompt in prompts:
            doc = _synthesize_parametric_cadir("test", prompt, {}, [])
            # Washer should have hole feature
            feature_types = [f.feature_type for f in doc.features]
            assert "hole" in feature_types, f"Washer prompt '{prompt}' should have hole"
    
    def test_nut_classification(self):
        """Nut keywords trigger nut geometry."""
        prompts = [
            "Create a hex nut",
            "Make a nut",
            "Design a hexagonal nut"
        ]
        
        for prompt in prompts:
            doc = _synthesize_parametric_cadir("test", prompt, {}, [])
            feature_types = [f.feature_type for f in doc.features]
            assert "hole" in feature_types, f"Nut prompt '{prompt}' should have hole"
    
    def test_shaft_classification(self):
        """Shaft keywords trigger cylinder geometry."""
        prompts = [
            "Create a shaft",
            "Make a rod",
            "Design a cylinder"
        ]
        
        for prompt in prompts:
            doc = _synthesize_parametric_cadir("test", prompt, {}, [])
            feature_types = [f.feature_type for f in doc.features]
            assert "cylinder" in feature_types, f"Shaft prompt '{prompt}' should have cylinder"
    
    def test_bracket_classification(self):
        """Bracket keywords trigger bracket geometry."""
        prompts = [
            "Create a mounting bracket",
            "Make a bracket",
            "Design an L-bracket"
        ]
        
        for prompt in prompts:
            doc = _synthesize_parametric_cadir("test", prompt, {}, [])
            # Brackets should have multiple features
            assert len(doc.features) >= 2, f"Bracket prompt '{prompt}' should have multiple features"


class TestGeometryVariation:
    """Test that hash-based variation works correctly."""
    
    def test_variation_produces_different_sizes(self):
        """Different prompts produce measurably different dimensions."""
        # Generate 10 different prompts
        prompts = [
            f"Create a simple box variant {i}"
            for i in range(10)
        ]
        
        dimensions_list = []
        for prompt in prompts:
            doc = _synthesize_parametric_cadir("test", prompt, {}, [])
            if doc.features:
                f = doc.features[0]
                dim = (
                    getattr(f, 'length', 0),
                    getattr(f, 'width', 0),
                    getattr(f, 'height', 0)
                )
                dimensions_list.append(dim)
        
        # Should have multiple unique dimension sets
        unique_dims = set(dimensions_list)
        assert len(unique_dims) > 1, "Different prompts should produce different dimensions"
    
    def test_variation_within_reasonable_bounds(self):
        """Variation should be reasonable (not extreme)."""
        prompt = "Create a box"
        doc = _synthesize_parametric_cadir("test", prompt, {}, [])
        
        f = doc.features[0]
        # Dimensions should be positive and reasonable
        assert 10 <= f.length <= 150, "Length should be within reasonable bounds"
        assert 10 <= f.width <= 120, "Width should be within reasonable bounds"
        assert 10 <= f.height <= 80, "Height should be within reasonable bounds"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
