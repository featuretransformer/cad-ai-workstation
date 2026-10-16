"""
End-to-end integration test for CAD generation pipeline.

Validates the complete flow:
  User Prompt → CADIR Document → build123d Code → Execution → STEP/STL Export

Tests the critical bug fix ensuring different prompts produce different final geometry.
"""
import pytest
import sys
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from agents.design_agent import design_agent_node
from agents.validator_nodes import (
    cadir_validator_node,
    interpreter_node,
    cad_executor_node,
    geometry_validator_node,
)


class TestEndToEndPipeline:
    """Test complete pipeline from prompt to exported geometry."""
    
    @pytest.fixture
    def test_prompts(self):
        """Different test prompts representing distinct mechanical parts."""
        return {
            "plate_with_hole": {
                "prompt": "Create a mounting plate 80mm x 60mm x 10mm with a 15mm diameter hole in the center",
                "expected_features": ["box", "hole"],
                "min_volume": 30000,  # mm³ (rough estimate allowing for hole)
            },
            "stepped_shaft": {
                "prompt": "Design a stepped shaft 12mm diameter and 100mm long",
                "expected_features": ["cylinder"],
                "min_volume": 10000,
            },
            "mounting_bracket": {
                "prompt": "Make a mounting bracket 50mm x 40mm with two mounting holes",
                "expected_features": ["box", "hole"],
                "min_volume": 15000,
            },
            "washer": {
                "prompt": "Create a washer with 30mm outer diameter, 15mm inner diameter, and 4mm thickness",
                "expected_features": ["extrude", "hole"],
                "min_volume": 1000,
            },
            "simple_block": {
                "prompt": "Make a rectangular block 25mm x 20mm x 15mm",
                "expected_features": ["box"],
                "min_volume": 6000,
            }
        }
    
    def run_full_pipeline(self, prompt: str, design_id: str) -> dict:
        """
        Run the complete agent pipeline for a given prompt.
        Returns the final state with all exports and validation.
        """
        # Initialize state
        state: AgentState = {
            "design_id": design_id,
            "user_prompt": prompt,
            "parsed_intent": {},
            "retrieved_examples": [],
            "max_retries": 3,
            "repair_attempts": 0,
            "confidence_scores": {},
        }
        
        # Step 1: Design Agent - Generate CADIR
        print(f"\n[{design_id}] Step 1: Design Agent")
        state.update(design_agent_node(state))
        assert state.get("cadir_document") is not None, "Design agent should produce CADIR document"
        
        # Step 2: CADIR Validator
        print(f"[{design_id}] Step 2: CADIR Validator")
        state.update(cadir_validator_node(state))
        if not state.get("cadir_valid"):
            errors = state.get("cadir_errors", [])
            pytest.fail(f"CADIR validation failed: {errors}")
        
        # Step 3: Interpreter - CADIR to build123d code
        print(f"[{design_id}] Step 3: Interpreter")
        state.update(interpreter_node(state))
        assert state.get("cad_code"), "Interpreter should produce build123d code"
        
        # Step 4: CAD Executor - Run build123d and export
        print(f"[{design_id}] Step 4: CAD Executor")
        state.update(cad_executor_node(state))
        exec_result = state.get("execution_result", {})
        
        if not exec_result.get("success"):
            error = exec_result.get("error", "Unknown error")
            stdout = exec_result.get("stdout", "")
            stderr = exec_result.get("stderr", "")
            pytest.fail(
                f"CAD execution failed:\n"
                f"Error: {error}\n"
                f"Stdout: {stdout}\n"
                f"Stderr: {stderr}"
            )
        
        # Step 5: Geometry Validator
        print(f"[{design_id}] Step 5: Geometry Validator")
        state.update(geometry_validator_node(state))
        
        if not state.get("geometry_valid"):
            errors = state.get("validation_errors", [])
            print(f"[{design_id}] Validation warnings: {errors}")
            # Don't fail on warnings, just log them
        
        return state
    
    def test_different_prompts_produce_different_files(self, test_prompts):
        """
        CRITICAL TEST: Verify different prompts produce different STEP files.
        This is the main regression test for the duplicate geometry bug.
        """
        results = {}
        
        # Run pipeline for each test prompt
        for name, config in test_prompts.items():
            print(f"\n{'='*60}")
            print(f"Testing: {name}")
            print(f"Prompt: {config['prompt']}")
            print(f"{'='*60}")
            
            state = self.run_full_pipeline(config["prompt"], f"test_{name}")
            results[name] = state
        
        # Extract STEP file paths
        step_paths = {}
        for name, state in results.items():
            exec_result = state.get("execution_result", {})
            step_path = exec_result.get("step_path")
            assert step_path, f"{name}: No STEP file generated"
            assert Path(step_path).exists(), f"{name}: STEP file {step_path} does not exist"
            step_paths[name] = step_path
        
        # Compare file sizes - different geometries should have different file sizes
        file_sizes = {}
        for name, path in step_paths.items():
            size = Path(path).stat().st_size
            file_sizes[name] = size
            print(f"\n{name}: {size} bytes")
        
        # All files should have different sizes (strong indicator of different geometry)
        unique_sizes = set(file_sizes.values())
        assert len(unique_sizes) == len(file_sizes), (
            f"REGRESSION: Different prompts produced identical file sizes!\n"
            f"File sizes: {file_sizes}\n"
            f"This indicates the geometry generation bug is not fixed."
        )
        
        print(f"\n✓ All {len(test_prompts)} prompts produced unique geometries")
    
    def test_identical_prompts_produce_identical_geometry(self):
        """Verify identical prompts produce consistent results."""
        prompt = "Create a mounting plate 70mm x 50mm x 8mm with a 10mm hole"
        
        # Run twice with same prompt
        state1 = self.run_full_pipeline(prompt, "identical_test_1")
        state2 = self.run_full_pipeline(prompt, "identical_test_2")
        
        # Extract volumes
        vol1 = state1.get("execution_result", {}).get("volume", 0)
        vol2 = state2.get("execution_result", {}).get("volume", 0)
        
        # Volumes should be identical (allowing tiny floating point error)
        assert abs(vol1 - vol2) < 0.01, (
            f"Identical prompts produced different volumes: {vol1} vs {vol2}"
        )
        
        # Feature counts should match
        ftree1 = state1.get("feature_tree", [])
        ftree2 = state2.get("feature_tree", [])
        assert len(ftree1) == len(ftree2), "Feature counts should match"
        
        print(f"✓ Identical prompts produced consistent geometry (volume: {vol1:.2f} mm³)")
    
    def test_explicit_dimensions_respected(self):
        """Verify explicit dimensions in prompt are used in final geometry."""
        prompt = "Create a box 100mm x 50mm x 25mm"
        state = self.run_full_pipeline(prompt, "explicit_dims_test")
        
        # Extract bounding box
        exec_result = state.get("execution_result", {})
        bbox = exec_result.get("bounding_box", {})
        
        # Calculate dimensions from bounding box
        length = bbox["xmax"] - bbox["xmin"]
        width = bbox["ymax"] - bbox["ymin"]
        height = bbox["zmax"] - bbox["zmin"]
        
        # Should match specified dimensions (with small tolerance)
        assert abs(length - 100.0) < 1.0, f"Length should be ~100mm, got {length:.2f}"
        assert abs(width - 50.0) < 1.0, f"Width should be ~50mm, got {width:.2f}"
        assert abs(height - 25.0) < 1.0, f"Height should be ~25mm, got {height:.2f}"
        
        print(f"✓ Explicit dimensions respected: {length:.1f} x {width:.1f} x {height:.1f} mm")
    
    def test_volume_sanity_checks(self, test_prompts):
        """Verify generated geometries have reasonable volumes."""
        for name, config in test_prompts.items():
            state = self.run_full_pipeline(config["prompt"], f"volume_test_{name}")
            
            exec_result = state.get("execution_result", {})
            volume = exec_result.get("volume", 0)
            
            assert volume > 0, f"{name}: Volume should be positive"
            assert volume >= config["min_volume"], (
                f"{name}: Volume {volume:.2f} is less than expected minimum {config['min_volume']}"
            )
            
            print(f"{name}: volume = {volume:.2f} mm³ ✓")
    
    def test_step_file_validity(self, test_prompts):
        """Verify all generated STEP files are valid."""
        for name, config in test_prompts.items():
            state = self.run_full_pipeline(config["prompt"], f"step_validity_{name}")
            
            step_path = state.get("execution_result", {}).get("step_path")
            assert step_path, f"{name}: No STEP path"
            
            # Read first few lines to verify STEP format
            with open(step_path, 'r') as f:
                header = f.read(100)
                assert "ISO-10303" in header, f"{name}: Invalid STEP header"
            
            print(f"{name}: Valid STEP file ✓")
    
    def test_geometry_validation_passes(self, test_prompts):
        """Verify all geometries pass validation (or only have warnings)."""
        for name, config in test_prompts.items():
            state = self.run_full_pipeline(config["prompt"], f"validation_{name}")
            
            # Geometry should be valid or have only warnings
            is_valid = state.get("geometry_valid", False)
            errors = state.get("validation_errors", [])
            
            if not is_valid and errors:
                # Check if errors are actually just warnings
                critical_errors = [e for e in errors if "warning" not in e.lower()]
                assert len(critical_errors) == 0, (
                    f"{name}: Critical validation errors: {critical_errors}"
                )
            
            print(f"{name}: Geometry validation passed ✓")


class TestRegressionScenarios:
    """Test specific scenarios that previously triggered the bug."""
    
    def test_two_simple_parts_are_different(self):
        """
        REGRESSION TEST: Previously, these two prompts generated identical geometry.
        Now they must be different.
        """
        prompt1 = "Create a simple mounting plate"
        prompt2 = "Make a basic bracket"
        
        # Run pipeline
        state1 = TestEndToEndPipeline().run_full_pipeline(prompt1, "regression_1")
        state2 = TestEndToEndPipeline().run_full_pipeline(prompt2, "regression_2")
        
        # Extract features
        doc1 = state1.get("cadir_document")
        doc2 = state2.get("cadir_document")
        
        # Feature dimensions should differ
        f1 = doc1.features[0]
        f2 = doc2.features[0]
        
        dims1 = (
            getattr(f1, 'length', None),
            getattr(f1, 'width', None),
            getattr(f1, 'height', None)
        )
        dims2 = (
            getattr(f2, 'length', None),
            getattr(f2, 'width', None),
            getattr(f2, 'height', None)
        )
        
        assert dims1 != dims2, (
            f"REGRESSION: Different prompts produced identical dimensions!\n"
            f"Prompt 1: {dims1}\n"
            f"Prompt 2: {dims2}"
        )
        
        print(f"✓ Regression test passed: different prompts → different geometry")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
