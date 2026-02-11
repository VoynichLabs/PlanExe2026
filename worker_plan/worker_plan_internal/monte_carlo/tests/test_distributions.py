"""
Unit tests for distribution samplers.

STRATEGY:
    For each distribution (triangular, PERT, lognormal):
    1. Sample 1000 values
    2. Verify bounds: min <= samples <= max
    3. Verify statistics: mean is reasonable, std dev is positive
    4. Verify mode location for triangular/PERT
    5. Test edge cases and error handling
"""

import unittest
import numpy as np
from worker_plan_internal.monte_carlo.distributions import (
    sample_triangular,
    sample_pert,
    sample_lognormal,
    compute_lognormal_params,
)


class TestTriangular(unittest.TestCase):
    """Test triangular distribution sampling."""

    def test_single_sample(self):
        """Single sample should be float in valid range."""
        sample = sample_triangular(min_val=1.0, mode_val=2.0, max_val=3.0, size=1)
        self.assertIsInstance(sample, (float, np.floating))
        self.assertGreaterEqual(sample, 1.0)
        self.assertLessEqual(sample, 3.0)

    def test_multiple_samples(self):
        """Multiple samples should return array."""
        samples = sample_triangular(
            min_val=1.0, mode_val=2.0, max_val=3.0, size=1000
        )
        self.assertIsInstance(samples, np.ndarray)
        self.assertEqual(samples.shape, (1000,))

    def test_bounds(self):
        """All samples must be within [min, max]."""
        samples = sample_triangular(
            min_val=0.0, mode_val=5.0, max_val=10.0, size=1000
        )
        self.assertTrue(np.all(samples >= 0.0))
        self.assertTrue(np.all(samples <= 10.0))

    def test_mean_is_reasonable(self):
        """Mean should be close to (min + mode + max) / 3."""
        min_v, mode_v, max_v = 1.0, 3.0, 6.0
        samples = sample_triangular(
            min_val=min_v, mode_val=mode_v, max_val=max_v, size=10000
        )
        expected_mean = (min_v + mode_v + max_v) / 3
        actual_mean = np.mean(samples)
        # Allow 5% tolerance due to random sampling
        self.assertAlmostEqual(actual_mean, expected_mean, delta=0.5)

    def test_mode_location(self):
        """When mode is at min, distribution should be skewed right."""
        samples_left_mode = sample_triangular(
            min_val=0.0, mode_val=0.5, max_val=10.0, size=10000
        )
        samples_right_mode = sample_triangular(
            min_val=0.0, mode_val=9.5, max_val=10.0, size=10000
        )

        # Left mode: median should be lower
        # Right mode: median should be higher
        left_median = np.median(samples_left_mode)
        right_median = np.median(samples_right_mode)

        self.assertLess(left_median, right_median)

    def test_reproducibility_with_seed(self):
        """Same seed should produce identical samples."""
        samples1 = sample_triangular(
            min_val=1.0, mode_val=2.0, max_val=3.0, size=100, random_state=42
        )
        samples2 = sample_triangular(
            min_val=1.0, mode_val=2.0, max_val=3.0, size=100, random_state=42
        )
        np.testing.assert_array_equal(samples1, samples2)

    def test_invalid_params_raises_error(self):
        """Invalid parameter order should raise ValueError."""
        with self.assertRaises(ValueError):
            # min > mode
            sample_triangular(min_val=3.0, mode_val=2.0, max_val=4.0)

        with self.assertRaises(ValueError):
            # mode > max
            sample_triangular(min_val=1.0, mode_val=4.0, max_val=3.0)


class TestPERT(unittest.TestCase):
    """Test PERT distribution sampling."""

    def test_single_sample(self):
        """Single sample should be float in valid range."""
        sample = sample_pert(min_val=1.0, likely_val=2.0, max_val=3.0, size=1)
        self.assertIsInstance(sample, (float, np.floating))
        self.assertGreaterEqual(sample, 1.0)
        self.assertLessEqual(sample, 3.0)

    def test_multiple_samples(self):
        """Multiple samples should return array."""
        samples = sample_pert(
            min_val=1.0, likely_val=2.0, max_val=3.0, size=1000
        )
        self.assertIsInstance(samples, np.ndarray)
        self.assertEqual(samples.shape, (1000,))

    def test_bounds(self):
        """All samples must be within [min, max]."""
        samples = sample_pert(
            min_val=0.0, likely_val=5.0, max_val=10.0, size=1000
        )
        self.assertTrue(np.all(samples >= 0.0))
        self.assertTrue(np.all(samples <= 10.0))

    def test_mean_close_to_pert_formula(self):
        """Mean should match PERT formula: (min + 4*likely + max) / 6."""
        min_v, likely_v, max_v = 1.0, 3.0, 6.0
        samples = sample_pert(
            min_val=min_v, likely_val=likely_v, max_val=max_v, size=10000,
            lambda_param=4.0
        )
        expected_mean = (min_v + 4 * likely_v + max_v) / 6
        actual_mean = np.mean(samples)
        # Allow 5% tolerance
        self.assertAlmostEqual(actual_mean, expected_mean, delta=0.5)

    def test_lambda_param_effect(self):
        """Larger lambda should concentrate around likely value."""
        samples_low_lambda = sample_pert(
            min_val=0.0, likely_val=5.0, max_val=10.0, size=5000, lambda_param=1.0
        )
        samples_high_lambda = sample_pert(
            min_val=0.0, likely_val=5.0, max_val=10.0, size=5000, lambda_param=8.0
        )

        # Higher lambda: narrower distribution, lower std dev
        self.assertLess(
            np.std(samples_high_lambda),
            np.std(samples_low_lambda)
        )

    def test_reproducibility_with_seed(self):
        """Same seed should produce identical samples."""
        samples1 = sample_pert(
            min_val=1.0, likely_val=2.0, max_val=3.0, size=100, random_state=42
        )
        samples2 = sample_pert(
            min_val=1.0, likely_val=2.0, max_val=3.0, size=100, random_state=42
        )
        np.testing.assert_array_equal(samples1, samples2)

    def test_invalid_params_raises_error(self):
        """Invalid parameter order should raise ValueError."""
        with self.assertRaises(ValueError):
            sample_pert(min_val=3.0, likely_val=2.0, max_val=4.0)

        with self.assertRaises(ValueError):
            sample_pert(min_val=1.0, likely_val=4.0, max_val=3.0)

    def test_invalid_lambda_raises_error(self):
        """Negative or zero lambda should raise ValueError."""
        with self.assertRaises(ValueError):
            sample_pert(
                min_val=1.0, likely_val=2.0, max_val=3.0, lambda_param=-1.0
            )


class TestLognormal(unittest.TestCase):
    """Test lognormal distribution sampling."""

    def test_single_sample(self):
        """Single sample should be positive float."""
        sample = sample_lognormal(mu=0.0, sigma=0.5, size=1)
        self.assertIsInstance(sample, (float, np.floating))
        self.assertGreater(sample, 0)

    def test_multiple_samples(self):
        """Multiple samples should return array."""
        samples = sample_lognormal(mu=0.0, sigma=0.5, size=1000)
        self.assertIsInstance(samples, np.ndarray)
        self.assertEqual(samples.shape, (1000,))

    def test_positive_values(self):
        """All samples must be positive."""
        samples = sample_lognormal(mu=1.0, sigma=0.5, size=1000)
        self.assertTrue(np.all(samples > 0))

    def test_mean_relationship(self):
        """Mean should roughly match exp(mu + sigma^2 / 2)."""
        mu, sigma = 1.0, 0.5
        samples = sample_lognormal(mu=mu, sigma=sigma, size=10000)

        # Theoretical mean: E[X] = exp(mu + sigma^2 / 2)
        expected_mean = np.exp(mu + sigma ** 2 / 2)
        actual_mean = np.mean(samples)

        # Lognormal has high variance, allow 10% tolerance
        self.assertAlmostEqual(actual_mean, expected_mean, delta=0.1 * expected_mean)

    def test_right_skew(self):
        """Lognormal should be right-skewed (mean > median)."""
        samples = sample_lognormal(mu=0.0, sigma=0.8, size=5000)
        mean = np.mean(samples)
        median = np.median(samples)

        # Lognormal is always right-skewed
        self.assertGreater(mean, median)

    def test_reproducibility_with_seed(self):
        """Same seed should produce identical samples."""
        samples1 = sample_lognormal(mu=1.0, sigma=0.5, size=100, random_state=42)
        samples2 = sample_lognormal(mu=1.0, sigma=0.5, size=100, random_state=42)
        np.testing.assert_array_equal(samples1, samples2)

    def test_invalid_sigma_raises_error(self):
        """Non-positive sigma should raise ValueError."""
        with self.assertRaises(ValueError):
            sample_lognormal(mu=1.0, sigma=0.0)

        with self.assertRaises(ValueError):
            sample_lognormal(mu=1.0, sigma=-0.5)

    def test_non_finite_params_raise_error(self):
        """Infinite or NaN parameters should raise ValueError."""
        with self.assertRaises(ValueError):
            sample_lognormal(mu=np.inf, sigma=0.5)

        with self.assertRaises(ValueError):
            sample_lognormal(mu=np.nan, sigma=0.5)


class TestComputeLognormalParams(unittest.TestCase):
    """Test lognormal parameter conversion."""

    def test_basic_conversion(self):
        """Should convert mean/std to mu/sigma."""
        mean, std_dev = 10.0, 2.0
        mu, sigma = compute_lognormal_params(mean, std_dev)

        # Verify by sampling and checking
        samples = sample_lognormal(mu, sigma, size=1000)
        sampled_mean = np.mean(samples)
        sampled_std = np.std(samples)

        # Allow 5% tolerance
        self.assertAlmostEqual(sampled_mean, mean, delta=0.5)
        self.assertAlmostEqual(sampled_std, std_dev, delta=0.5)

    def test_zero_std_dev(self):
        """Zero std dev should give sigma near 0."""
        mu, sigma = compute_lognormal_params(10.0, 0.0)
        self.assertAlmostEqual(sigma, 0.0, places=5)

    def test_invalid_mean_raises_error(self):
        """Non-positive mean should raise ValueError."""
        with self.assertRaises(ValueError):
            compute_lognormal_params(0.0, 1.0)

        with self.assertRaises(ValueError):
            compute_lognormal_params(-5.0, 1.0)

    def test_negative_std_dev_raises_error(self):
        """Negative std dev should raise ValueError."""
        with self.assertRaises(ValueError):
            compute_lognormal_params(10.0, -1.0)


class TestDistributionStatistics(unittest.TestCase):
    """Integration tests for distribution statistics."""

    def test_triangular_variance_relationship(self):
        """Triangular variance should follow known formula."""
        # Var = (a + b + c - ab - ac - bc) / 18
        a, b, c = 1.0, 3.0, 5.0
        samples = sample_triangular(min_val=a, mode_val=b, max_val=c, size=10000)

        expected_var = (
            (a ** 2 + b ** 2 + c ** 2 - a * b - a * c - b * c) / 18
        )
        actual_var = np.var(samples)

        # Allow 10% tolerance
        self.assertAlmostEqual(actual_var, expected_var, delta=0.1 * expected_var)

    def test_lognormal_cv_effect(self):
        """Higher coefficient of variation should mean wider distribution."""
        # Create two lognormal distributions with different CVs
        mu1, sigma1 = compute_lognormal_params(100, 10)  # CV = 0.1
        mu2, sigma2 = compute_lognormal_params(100, 50)  # CV = 0.5

        samples1 = sample_lognormal(mu1, sigma1, size=5000)
        samples2 = sample_lognormal(mu2, sigma2, size=5000)

        # Higher CV should have wider range
        range1 = np.max(samples1) - np.min(samples1)
        range2 = np.max(samples2) - np.min(samples2)
        self.assertLess(range1, range2)


if __name__ == "__main__":
    unittest.main()
