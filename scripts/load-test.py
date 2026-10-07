#!/usr/bin/env python3
"""
CAD Pipeline Load Test
Tests the production system with multiple mechanical engineering designs
Validates performance, reliability, and correctness across various part types
"""
import asyncio
import time
import json
import sys
from typing import List, Dict
import httpx
from dataclasses import dataclass, asdict
from datetime import datetime


# ═══════════════════════════════════════════════════════
# TEST SCENARIOS - Mechanical Engineering Parts
# ═══════════════════════════════════════════════════════

TEST_SCENARIOS = [
    {
        "name": "Simple Washer",
        "prompt": "Create a flat washer with outer diameter 30mm, inner diameter 10mm, and thickness 4mm",
        "expected_features": ["extrude", "hole"],
        "timeout": 120,
    },
    {
        "name": "Hex Nut",
        "prompt": "Design a hexagonal nut M10 with height 8mm and across-flats 17mm",
        "expected_features": ["extrude", "hole"],
        "timeout": 120,
    },
    {
        "name": "Mounting Plate",
        "prompt": "Create a rectangular mounting plate 100mm x 60mm x 10mm with four M6 holes at corners",
        "expected_features": ["box", "hole"],
        "timeout": 150,
    },
    {
        "name": "Cylindrical Pin",
        "prompt": "Design a cylindrical dowel pin diameter 8mm, length 40mm with 0.5mm chamfer on both ends",
        "expected_features": ["cylinder", "chamfer"],
        "timeout": 120,
    },
    {
        "name": "L-Bracket",
        "prompt": "Create an L-shaped bracket with both legs 50mm long, thickness 6mm, with fillet radius 4mm",
        "expected_features": ["extrude", "fillet"],
        "timeout": 150,
    },
]


@dataclass
class TestResult:
    scenario: str
    success: bool
    duration_seconds: float
    design_id: str = None
    geometry_valid: bool = False
    error: str = None
    dfm_score: float = 0.0
    cost_usd: float = 0.0
    
    def to_dict(self):
        return asdict(self)


# ═══════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════

class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        self.results: List[TestResult] = []
    
    async def setup(self):
        """Create test session."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/sessions",
                json={"name": f"Load Test - {datetime.now().isoformat()}"}
            )
            response.raise_for_status()
            data = response.json()
            self.session_id = data["id"]
            print(f"✅ Created test session: {self.session_id}")
    
    async def run_scenario(self, scenario: Dict) -> TestResult:
        """Run a single test scenario."""
        print(f"\n🔧 Testing: {scenario['name']}")
        print(f"   Prompt: {scenario['prompt']}")
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=scenario["timeout"]) as client:
                # 1. Initiate design generation
                response = await client.post(
                    f"{self.base_url}/api/design/generate",
                    json={
                        "session_id": self.session_id,
                        "prompt": scenario["prompt"]
                    }
                )
                response.raise_for_status()
                data = response.json()
                design_id = data["design_id"]
                task_id = data["task_id"]
                
                print(f"   📋 Design ID: {design_id}")
                
                # 2. Poll for completion
                max_wait = scenario["timeout"]
                poll_interval = 5
                elapsed = 0
                
                while elapsed < max_wait:
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                    
                    # Check design status
                    response = await client.get(
                        f"{self.base_url}/api/design/{design_id}"
                    )
                    response.raise_for_status()
                    design = response.json()
                    
                    status = design.get("status", "PENDING")
                    print(f"   ⏳ Status: {status} ({elapsed}s)")
                    
                    if status == "COMPLETE":
                        duration = time.time() - start_time
                        
                        # Extract metrics
                        geometry_valid = design.get("geometry_valid", False)
                        dfm_report = design.get("dfm_report", {})
                        cost_estimate = design.get("cost_estimate", {})
                        
                        dfm_score = dfm_report.get("overall_score", 0.0)
                        cost = cost_estimate.get("total_unit_cost_usd", 0.0)
                        
                        print(f"   ✅ Completed in {duration:.2f}s")
                        print(f"      Geometry Valid: {geometry_valid}")
                        print(f"      DFM Score: {dfm_score}/100")
                        print(f"      Est. Cost: ${cost:.2f}")
                        
                        return TestResult(
                            scenario=scenario["name"],
                            success=True,
                            duration_seconds=duration,
                            design_id=design_id,
                            geometry_valid=geometry_valid,
                            dfm_score=dfm_score,
                            cost_usd=cost,
                        )
                    
                    elif status == "FAILED":
                        duration = time.time() - start_time
                        print(f"   ❌ Failed after {duration:.2f}s")
                        return TestResult(
                            scenario=scenario["name"],
                            success=False,
                            duration_seconds=duration,
                            design_id=design_id,
                            error="Design generation failed"
                        )
                
                # Timeout
                duration = time.time() - start_time
                print(f"   ⏰ Timeout after {duration:.2f}s")
                return TestResult(
                    scenario=scenario["name"],
                    success=False,
                    duration_seconds=duration,
                    design_id=design_id,
                    error=f"Timeout after {max_wait}s"
                )
        
        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ Exception: {str(e)}")
            return TestResult(
                scenario=scenario["name"],
                success=False,
                duration_seconds=duration,
                error=str(e)
            )
    
    async def run_all(self):
        """Run all test scenarios."""
        print("\n" + "="*60)
        print("🚀 CAD PIPELINE LOAD TEST")
        print("="*60)
        
        await self.setup()
        
        for scenario in TEST_SCENARIOS:
            result = await self.run_scenario(scenario)
            self.results.append(result)
        
        self.print_summary()
        self.save_results()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 LOAD TEST SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success and r.geometry_valid)
        failed = total - passed
        
        total_duration = sum(r.duration_seconds for r in self.results)
        avg_duration = total_duration / total if total > 0 else 0
        
        print(f"\nTotal Tests:     {total}")
        print(f"✅ Passed:       {passed} ({passed/total*100:.1f}%)")
        print(f"❌ Failed:       {failed} ({failed/total*100:.1f}%)")
        print(f"\nTotal Time:      {total_duration:.2f}s")
        print(f"Avg Time:        {avg_duration:.2f}s per design")
        
        # Per-scenario results
        print("\n" + "-"*60)
        print("SCENARIO RESULTS:")
        print("-"*60)
        
        for result in self.results:
            status = "✅ PASS" if result.success and result.geometry_valid else "❌ FAIL"
            print(f"\n{status} {result.scenario}")
            print(f"  Duration:  {result.duration_seconds:.2f}s")
            print(f"  Valid Geo: {result.geometry_valid}")
            if result.dfm_score > 0:
                print(f"  DFM Score: {result.dfm_score:.1f}/100")
            if result.cost_usd > 0:
                print(f"  Est. Cost: ${result.cost_usd:.2f}")
            if result.error:
                print(f"  Error:     {result.error}")
        
        print("\n" + "="*60)
        
        # Performance metrics
        valid_results = [r for r in self.results if r.success and r.geometry_valid]
        if valid_results:
            avg_dfm = sum(r.dfm_score for r in valid_results) / len(valid_results)
            avg_cost = sum(r.cost_usd for r in valid_results) / len(valid_results)
            
            print("\n📈 PERFORMANCE METRICS (Valid Designs Only):")
            print(f"  Avg DFM Score:      {avg_dfm:.1f}/100")
            print(f"  Avg Cost Estimate:  ${avg_cost:.2f}")
            print(f"  Avg Generation Time: {sum(r.duration_seconds for r in valid_results) / len(valid_results):.2f}s")
    
    def save_results(self):
        """Save results to JSON file."""
        filename = f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r.success and r.geometry_valid),
            "results": [r.to_dict() for r in self.results]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

async def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    tester = LoadTester(base_url=base_url)
    await tester.run_all()
    
    # Exit code based on results
    passed = sum(1 for r in tester.results if r.success and r.geometry_valid)
    total = len(tester.results)
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    elif passed >= total * 0.8:
        print(f"\n⚠️  {passed}/{total} tests passed (80%+)")
        sys.exit(0)
    else:
        print(f"\n❌ Only {passed}/{total} tests passed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
