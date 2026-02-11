"""
Unit tests for risk event sampling.

STRATEGY:
    For Bernoulli and impact sampling:
    1. Test pure Bernoulli: verify probability of occurrence
    2. Test impact sampling: verify impact distribution
    3. Test combined: verify zero impacts when event doesn't occur
    4. Test portfolio: verify independent events combine properly
    5. Test edge cases and error handling
"""

import unittest
import numpy as np
from worker_plan_internal.monte_carlo.risk_events import (
    sample_bernoulli_impact,
    sample_risk_event,
    sample_portfolio_risk,
)
from worker_plan_internal.monte_carlo.distributions import sample_triangular


class TestBernoulliImpact(unittest.TestCase):
    """Test Bernoulli occurrence + impact sampling."""

    def test_single_sample_with_occurrence(self):
        """Single sample should return float."""
        impact = sample_bernoulli_impact(
            probability=1.0,  # Event guaranteed to occur
            impact_fn=lambda: 5.0,  # Fixed impact
            size=1
        )
        self.assertIsInstance(impact, (float, np.floating))
        self.assertEqual(impact, 5.0)

    def test_single_sample_without_occurrence(self):
        """With p=0, impact should always be 0."""
        impact = sample_bernoulli_impact(
            probability=0.0,  # Event never occurs
            impact_fn=lambda: 5.0,
            size=1
        )
        self.assertEqual(impact, 0.0)

    def test_multiple_samples(self):
        """Multiple samples should return array."""
        impacts = sample_bernoulli_impact(
            probability=0.5,
            impact_fn=lambda: 5.0,
            size=100
        )
        self.assertIsInstance(impacts, np.ndarray)
        self.assertEqual(impacts.shape, (100,))

    def test_probability_accuracy(self):
        """Frequency of non-zero impacts should match probability."""
        prob = 0.3
        samples = sample_bernoulli_impact(
            probability=prob,
            impact_fn=lambda: 10.0,  # All impacts are 10.0
            size=10000
        )

        # Count non-zero impacts
        num_occurrences = np.sum(samples != 0)
        actual_prob = num_occurrences / 10000

        # Allow 2% tolerance
        self.assertAlmostEqual(actual_prob, prob, delta=0.02)

    def test_impact_values_respected(self):
        """Impact distribution should be sampled correctly."""
        # Create a sampler that always returns values in [5, 10]
        call_count = [0]

        def impact_fn():
            call_count[0] += 1
            return float(call_count[0] % 5 + 5)

        samples = sample_bernoulli_impact(
            probability=1.0,  # All events occur
            impact_fn=impact_fn,
            size=100
        )

        # All non-zero values should be in [5, 10)
        non_zero = samples[samples != 0]
        self.assertTrue(np.all(non_zero >= 5))
        self.assertTrue(np.all(non_zero < 10))

    def test_zero_impacts_when_no_occurrence(self):
        """When event doesn't occur, impact is always 0."""
        samples = sample_bernoulli_impact(
            probability=0.0,
            impact_fn=lambda: 100.0,  # Would be huge if occurred
            size=1000
        )

        # All should be 0
        self.assertTrue(np.all(samples == 0))

    def test_reproducibility_with_seed(self):
        """Same seed should produce identical samples."""
        samples1 = sample_bernoulli_impact(
            probability=0.5,
            impact_fn=lambda: 5.0,
            size=100,
            random_state=42
        )
        samples2 = sample_bernoulli_impact(
            probability=0.5,
            impact_fn=lambda: 5.0,
            size=100,
            random_state=42
        )
        np.testing.assert_array_equal(samples1, samples2)

    def test_invalid_probability_raises_error(self):
        """Probability must be in [0, 1]."""
        with self.assertRaises(ValueError):
            sample_bernoulli_impact(
                probability=1.5,
                impact_fn=lambda: 5.0
            )

        with self.assertRaises(ValueError):
            sample_bernoulli_impact(
                probability=-0.1,
                impact_fn=lambda: 5.0
            )

    def test_non_callable_impact_raises_error(self):
        """Impact function must be callable."""
        with self.assertRaises(TypeError):
            sample_bernoulli_impact(
                probability=0.5,
                impact_fn=5.0  # Not callable!
            )


class TestRiskEvent(unittest.TestCase):
    """Test convenience wrapper for risk events."""

    def test_triangular_impact(self):
        """Should sample with triangular impact distribution."""
        samples = sample_risk_event(
            probability=0.5,
            impact_min=1.0,
            impact_max=10.0,
            impact_mode=5.0,
            impact_distribution="triangular",
            size=1000
        )

        self.assertEqual(samples.shape, (1000,))

        # Non-zero impacts should be in [1, 10]
        non_zero = samples[samples != 0]
        if len(non_zero) > 0:
            self.assertGreaterEqual(np.min(non_zero), 1.0)
            self.assertLessEqual(np.max(non_zero), 10.0)

    def test_lognormal_impact_with_params(self):
        """Should sample with lognormal impact distribution."""
        mu, sigma = 2.0, 0.5
        samples = sample_risk_event(
            probability=0.8,
            impact_min=1.0,  # Used for validation only
            impact_max=100.0,
            impact_distribution="lognormal",
            mu=mu,
            sigma=sigma,
            size=1000
        )

        self.assertEqual(samples.shape, (1000,))

        # All non-zero impacts should be positive
        non_zero = samples[samples != 0]
        if len(non_zero) > 0:
            self.assertTrue(np.all(non_zero > 0))

    def test_lognormal_impact_computed_params(self):
        """Should auto-compute lognormal params from min/max."""
        samples = sample_risk_event(
            probability=0.5,
            impact_min=5.0,
            impact_max=20.0,
            impact_distribution="lognormal",
            size=1000
        )

        self.assertEqual(samples.shape, (1000,))

        # Non-zero impacts should be roughly in [5, 20]
        non_zero = samples[samples != 0]
        if len(non_zero) > 0:
            self.assertTrue(np.all(non_zero > 0))

    def test_invalid_distribution_raises_error(self):
        """Unknown distribution type should raise ValueError."""
        with self.assertRaises(ValueError):
            sample_risk_event(
                probability=0.5,
                impact_min=1.0,
                impact_max=10.0,
                impact_distribution="invalid_type"
            )

    def test_triangular_missing_mode_raises_error(self):
        """Triangular requires impact_mode parameter."""
        with self.assertRaises(ValueError):
            sample_risk_event(
                probability=0.5,
                impact_min=1.0,
                impact_max=10.0,
                impact_distribution="triangular"
                # Missing impact_mode!
            )

    def test_invalid_triangular_params_raises_error(self):
        """Invalid triangular parameter order should raise ValueError."""
        with self.assertRaises(ValueError):
            sample_risk_event(
                probability=0.5,
                impact_min=10.0,
                impact_max=1.0,  # max < min
                impact_mode=5.0,
                impact_distribution="triangular"
            )

    def test_lognormal_negative_bounds_raises_error(self):
        """Lognormal requires positive bounds (if no mu/sigma)."""
        with self.assertRaises(ValueError):
            sample_risk_event(
                probability=0.5,
                impact_min=-5.0,  # Negative
                impact_max=10.0,
                impact_distribution="lognormal"
            )


class TestPortfolioRisk(unittest.TestCase):
    """Test sampling multiple risk events together."""

    def test_single_event(self):
        """Portfolio with one event should match single event."""
        risk_events = [
            {
                "probability": 0.5,
                "impact_fn": lambda: 10.0
            }
        ]

        samples = sample_portfolio_risk(risk_events, size=1000)

        self.assertEqual(samples.shape, (1000,))

        # Probability of non-zero should be ~0.5
        num_non_zero = np.sum(samples != 0)
        prob = num_non_zero / 1000
        self.assertAlmostEqual(prob, 0.5, delta=0.05)

    def test_independent_events_sum(self):
        """Multiple events should sum independently."""
        risk_events = [
            {
                "probability": 1.0,  # Always occurs
                "impact_fn": lambda: 5.0
            },
            {
                "probability": 1.0,  # Always occurs
                "impact_fn": lambda: 3.0
            }
        ]

        samples = sample_portfolio_risk(risk_events, size=1000)

        # All should be 8.0 (5 + 3)
        np.testing.assert_array_almost_equal(samples, 8.0)

    def test_zero_events(self):
        """Empty risk list should return all zeros."""
        samples = sample_portfolio_risk([], size=100)
        np.testing.assert_array_equal(samples, np.zeros(100))

    def test_mixed_probabilities(self):
        """High prob event should contribute more frequently."""
        risk_events = [
            {
                "probability": 0.9,
                "impact_fn": lambda: 10.0
            },
            {
                "probability": 0.1,
                "impact_fn": lambda: 10.0
            }
        ]

        samples = sample_portfolio_risk(risk_events, size=5000)

        # Expected: ~90% chance of event1, ~10% of event2, ~9% both
        # Mean impact should be close to 0.9*10 + 0.1*10 = 10
        mean = np.mean(samples)
        # Allow 20% tolerance due to randomness
        self.assertGreater(mean, 8)
        self.assertLess(mean, 12)

    def test_reproducibility_with_seed(self):
        """Same seed should produce identical samples."""
        risk_events = [
            {
                "probability": 0.5,
                "impact_fn": lambda: 10.0
            }
        ]

        samples1 = sample_portfolio_risk(
            risk_events, size=100, random_state=42
        )
        samples2 = sample_portfolio_risk(
            risk_events, size=100, random_state=42
        )

        np.testing.assert_array_equal(samples1, samples2)


class TestRiskEventIntegration(unittest.TestCase):
    """Integration tests combining distributions with risk events."""

    def test_triangular_impact_distribution(self):
        """Risk event with triangular impact."""
        def triangular_impact():
            return sample_triangular(min_val=1.0, mode_val=5.0, max_val=10.0)

        samples = sample_bernoulli_impact(
            probability=0.7,
            impact_fn=triangular_impact,
            size=2000
        )

        # Check probability
        prob = np.sum(samples != 0) / 2000
        self.assertAlmostEqual(prob, 0.7, delta=0.05)

        # Check impact bounds
        non_zero = samples[samples != 0]
        if len(non_zero) > 0:
            self.assertGreaterEqual(np.min(non_zero), 1.0)
            self.assertLessEqual(np.max(non_zero), 10.0)

    def test_scenario_with_multiple_risks(self):
        """Realistic scenario: multiple independent risks."""
        # Risk 1: Regulatory delay (60% probability, 2-10 week impact)
        # Risk 2: Resource shortage (30% probability, 5-15% cost overrun)
        # Risk 3: Technical challenge (40% probability, 1-3 week delay)

        risk_events = [
            {
                "probability": 0.6,
                "impact_fn": lambda: sample_triangular(2, 5, 10)
            },
            {
                "probability": 0.3,
                "impact_fn": lambda: sample_triangular(5, 10, 15)
            },
            {
                "probability": 0.4,
                "impact_fn": lambda: sample_triangular(1, 2, 3)
            }
        ]

        samples = sample_portfolio_risk(risk_events, size=5000)

        self.assertEqual(samples.shape, (5000,))

        # All impacts should be non-negative
        self.assertTrue(np.all(samples >= 0))

        # Mean should be positive but reasonable
        mean = np.mean(samples)
        self.assertGreater(mean, 0)
        self.assertLess(mean, 50)  # Not unreasonably high


if __name__ == "__main__":
    unittest.main()
