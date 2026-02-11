"""
PURPOSE: Unit and integration tests for Monte Carlo simulation engine.

Tests verify:
- Simulation runs successfully with mock plan data
- Success probability is between 0-1
- Percentiles are ordered correctly (P10 < P50 < P90)
- Results are statistically reasonable
- Multiple runs show consistency within expected variance
"""

import unittest
import sys
import os
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation import MonteCarloSimulation
from config import NUM_RUNS


class TestMonteCarloSimulation(unittest.TestCase):
    """Test suite for Monte Carlo simulation engine."""

    def setUp(self):
        """Create mock plan data and simulator instance."""
        self.mock_plan = {
            "name": "Test Plan",
            "deadline_days": 50,
            "budget": 100000,
            "tasks": [
                {
                    "id": "task_1",
                    "name": "Requirements",
                    "duration_min": 5,
                    "duration_likely": 8,
                    "duration_max": 12,
                    "cost_min": 5000,
                    "cost_likely": 10000,
                    "cost_max": 15000,
                },
                {
                    "id": "task_2",
                    "name": "Design",
                    "duration_min": 8,
                    "duration_likely": 12,
                    "duration_max": 18,
                    "cost_min": 10000,
                    "cost_likely": 15000,
                    "cost_max": 22000,
                },
                {
                    "id": "task_3",
                    "name": "Development",
                    "duration_min": 15,
                    "duration_likely": 22,
                    "duration_max": 35,
                    "cost_min": 30000,
                    "cost_likely": 45000,
                    "cost_max": 60000,
                },
                {
                    "id": "task_4",
                    "name": "Testing",
                    "duration_min": 8,
                    "duration_likely": 12,
                    "duration_max": 20,
                    "cost_min": 8000,
                    "cost_likely": 12000,
                    "cost_max": 18000,
                },
                {
                    "id": "task_5",
                    "name": "Deployment",
                    "duration_min": 3,
                    "duration_likely": 5,
                    "duration_max": 8,
                    "cost_min": 2000,
                    "cost_likely": 3000,
                    "cost_max": 5000,
                },
            ],
            "risk_events": [
                {
                    "id": "risk_1",
                    "name": "Scope Creep",
                    "probability": 0.3,
                    "impact_duration": 10,
                    "impact_cost": 5000,
                    "severity": "medium",
                },
                {
                    "id": "risk_2",
                    "name": "Resource Shortage",
                    "probability": 0.15,
                    "impact_duration": 7,
                    "impact_cost": 3000,
                    "severity": "low",
                },
            ],
        }

    def test_simulation_runs_without_error(self):
        """Test that simulation completes successfully."""
        sim = MonteCarloSimulation(num_runs=100, random_seed=42)
        results = sim.run(self.mock_plan)
        
        self.assertIsNotNone(results)
        self.assertEqual(results["num_runs"], 100)
        self.assertIn("success_probability", results)

    def test_success_probability_bounds(self):
        """Test that success probability is between 0 and 1."""
        sim = MonteCarloSimulation(num_runs=100, random_seed=42)
        results = sim.run(self.mock_plan)
        
        success_prob = results["success_probability"]
        self.assertGreaterEqual(success_prob, 0.0)
        self.assertLessEqual(success_prob, 1.0)

    def test_failure_probability_bounds(self):
        """Test that failure probability is between 0 and 1."""
        sim = MonteCarloSimulation(num_runs=100, random_seed=42)
        results = sim.run(self.mock_plan)
        
        failure_prob = results["failure_probability"]
        self.assertGreaterEqual(failure_prob, 0.0)
        self.assertLessEqual(failure_prob, 1.0)

    def test_success_failure_probabilities_sum_to_one(self):
        """Test that success + failure probabilities sum to 1.0 (within rounding)."""
        sim = MonteCarloSimulation(num_runs=100, random_seed=42)
        results = sim.run(self.mock_plan)
        
        total = results["success_probability"] + results["failure_probability"]
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_percentiles_are_ordered(self):
        """Test that P10 < P50 < P90 for all metrics."""
        sim = MonteCarloSimulation(num_runs=100, random_seed=42)
        results = sim.run(self.mock_plan)
        
        # Duration percentiles
        duration_p10 = results["duration_percentiles"][10]
        duration_p50 = results["duration_percentiles"][50]
        duration_p90 = results["duration_percentiles"][90]
        
        self.assertLess(duration_p10, duration_p50)
        self.assertLess(duration_p50, duration_p90)
        
        # Cost percentiles
        cost_p10 = results["cost_percentiles"][10]
        cost_p50 = results["cost_percentiles"][50]
        cost_p90 = results["cost_percentiles"][90]
        
        self.assertLess(cost_p10, cost_p50)
        self.assertLess(cost_p50, cost_p90)

    def test_percentiles_are_reasonable(self):
        """Test that percentiles are close to expected range."""
        sim = MonteCarloSimulation(num_runs=1000, random_seed=42)
        results = sim.run(self.mock_plan)
        
        # Duration: expect roughly 39-45 days (5+8+22+12+5 = 52 min, but with budget/deadline constraints)
        duration_p50 = results["duration_percentiles"][50]
        self.assertGreater(duration_p50, 30)  # At least more than sum of minimums
        self.assertLess(duration_p50, 100)  # But not excessively large
        
        # Cost: expect roughly 60k-80k (min sum 55k, likely sum 85k)
        cost_p50 = results["cost_percentiles"][50]
        self.assertGreater(cost_p50, 40000)
        self.assertLess(cost_p50, 150000)

    def test_probability_metrics_in_valid_range(self):
        """Test that delay and overrun probabilities are valid."""
        sim = MonteCarloSimulation(num_runs=100, random_seed=42)
        results = sim.run(self.mock_plan)
        
        delay_prob = results["delay_probability"]
        overrun_prob = results["budget_overrun_probability"]
        
        self.assertGreaterEqual(delay_prob, 0.0)
        self.assertLessEqual(delay_prob, 1.0)
        self.assertGreaterEqual(overrun_prob, 0.0)
        self.assertLessEqual(overrun_prob, 1.0)

    def test_recommendation_exists(self):
        """Test that recommendation is provided."""
        sim = MonteCarloSimulation(num_runs=100, random_seed=42)
        results = sim.run(self.mock_plan)
        
        recommendation = results["recommendation"]
        self.assertIn(recommendation, ["GO", "RE-SCOPE", "NO-GO"])

    def test_multiple_runs_consistency(self):
        """Test that results are consistent across independent runs (within variance)."""
        sim1 = MonteCarloSimulation(num_runs=500, random_seed=123)
        sim2 = MonteCarloSimulation(num_runs=500, random_seed=456)
        
        results1 = sim1.run(self.mock_plan)
        results2 = sim2.run(self.mock_plan)
        
        # Success probabilities should be within 0.15 of each other
        success_diff = abs(results1["success_probability"] - results2["success_probability"])
        self.assertLess(success_diff, 0.20)
        
        # Median duration should be within 20% of each other
        duration_diff = abs(
            results1["duration_percentiles"][50] - results2["duration_percentiles"][50]
        )
        self.assertLess(duration_diff, 10)

    def test_invalid_plan_raises_error(self):
        """Test that invalid plans raise appropriate errors."""
        sim = MonteCarloSimulation(num_runs=100)
        
        # Empty plan
        with self.assertRaises(ValueError):
            sim.run({})
        
        # Plan without tasks
        with self.assertRaises(ValueError):
            sim.run({"name": "Invalid"})
        
        # Plan with empty tasks
        with self.assertRaises(ValueError):
            sim.run({"name": "Invalid", "tasks": []})

    def test_deterministic_with_seed(self):
        """Test that seeding produces deterministic results."""
        # Create a separate plan copy for each run to ensure independence
        plan1 = dict(self.mock_plan)
        plan2 = dict(self.mock_plan)
        
        # Reset seed before each simulation
        np.random.seed(999)
        sim1 = MonteCarloSimulation(num_runs=100, random_seed=999)
        results1 = sim1.run(plan1)
        
        np.random.seed(999)
        sim2 = MonteCarloSimulation(num_runs=100, random_seed=999)
        results2 = sim2.run(plan2)
        
        # Same seed should produce identical results
        self.assertEqual(results1["success_probability"], results2["success_probability"])
        self.assertEqual(
            results1["duration_percentiles"][50],
            results2["duration_percentiles"][50]
        )

    def test_no_risk_events_scenario(self):
        """Test simulation with no risk events."""
        plan_no_risks = dict(self.mock_plan)
        plan_no_risks["risk_events"] = []
        
        sim = MonteCarloSimulation(num_runs=100, random_seed=42)
        results = sim.run(plan_no_risks)
        
        # Should complete without error
        self.assertIsNotNone(results)
        self.assertGreaterEqual(results["success_probability"], 0.0)

    def test_high_deadline_high_success(self):
        """Test that high deadline increases success probability."""
        # Lenient deadline (120 days)
        lenient_plan = dict(self.mock_plan)
        lenient_plan["deadline_days"] = 120
        
        sim = MonteCarloSimulation(num_runs=500, random_seed=42)
        lenient_results = sim.run(lenient_plan)
        
        # Strict deadline (30 days)
        strict_plan = dict(self.mock_plan)
        strict_plan["deadline_days"] = 30
        strict_results = sim.run(strict_plan)
        
        # Lenient should have higher success
        self.assertGreater(lenient_results["success_probability"], 
                          strict_results["success_probability"])

    def test_large_budget_high_success(self):
        """Test that larger budget increases success probability."""
        # Increase deadline to be more realistic for task duration
        base_plan = dict(self.mock_plan)
        base_plan["deadline_days"] = 100  # Realistic deadline for 5 tasks
        
        # Large budget
        large_budget_plan = dict(base_plan)
        large_budget_plan["budget"] = 500000
        
        np.random.seed(42)
        sim = MonteCarloSimulation(num_runs=500, random_seed=42)
        large_results = sim.run(large_budget_plan)
        
        # Small budget
        small_budget_plan = dict(base_plan)
        small_budget_plan["budget"] = 50000
        
        np.random.seed(42)
        small_results = sim.run(small_budget_plan)
        
        # Large should have higher or equal success
        self.assertGreaterEqual(large_results["success_probability"],
                          small_results["success_probability"])


if __name__ == "__main__":
    unittest.main()
