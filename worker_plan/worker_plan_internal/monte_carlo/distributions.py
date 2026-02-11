"""
PURPOSE: Probabilistic distribution samplers for task duration and cost uncertainty.

RESPONSIBILITIES:
- Sample task durations from triangular distribution (min, likely, max)
- Sample costs from lognormal distribution (estimate + variance factor)
- Sample durations from PERT distribution (alternative to triangular)
- Single responsibility: only sampling, no I/O or aggregation
"""

import numpy as np
from scipy.stats import triang, lognorm


class DurationSampler:
    """Samples task durations using triangular distribution."""

    @staticmethod
    def sample_triangular(min_duration, likely_duration, max_duration, size=1):
        """
        Sample from triangular distribution.
        
        Args:
            min_duration: Minimum duration (left bound)
            likely_duration: Most likely duration (peak)
            max_duration: Maximum duration (right bound)
            size: Number of samples to draw
            
        Returns:
            numpy array of sampled durations
        """
        # Scipy triangular requires normalized parameters: c = (mode - a) / (b - a)
        a = min_duration
        b = max_duration
        c = (likely_duration - a) / (b - a)
        
        # Clamp c to [0, 1] for edge cases
        c = np.clip(c, 0.0, 1.0)
        
        return triang.rvs(c, loc=a, scale=b - a, size=size)

    @staticmethod
    def sample_pert(min_duration, likely_duration, max_duration, size=1, alpha=4):
        """
        Sample from PERT (Program Evaluation and Review Technique) distribution.
        PERT is a beta distribution parameterized by min, likely, max.
        
        Args:
            min_duration: Minimum duration
            likely_duration: Most likely duration
            max_duration: Maximum duration
            size: Number of samples
            alpha: Shape parameter (default 4, common in PERT)
            
        Returns:
            numpy array of sampled durations
        """
        # PERT uses beta distribution with derived parameters
        # Expected value = (min + 4*likely + max) / 6
        # Variance ∝ (max - min)^2 / 36 / alpha
        
        a = min_duration
        b = max_duration
        m = likely_duration
        
        # Convert to beta distribution parameters
        # Beta (α, β) mapped to [a, b]
        beta_mean = (m - a) / (b - a)
        
        # Standard PERT formulation: alpha = beta = 4
        # This gives symmetry around mode; adjust for skew as needed
        beta_alpha = alpha
        beta_beta = alpha
        
        # Sample from beta and transform to [a, b]
        beta_samples = np.random.beta(beta_alpha, beta_beta, size=size)
        return a + (b - a) * beta_samples


class CostSampler:
    """Samples costs using lognormal and PERT distributions."""

    @staticmethod
    def sample_lognormal(estimate, variance_factor=0.2, size=1):
        """
        Sample from lognormal distribution for costs.
        
        Uses parametrization: if X ~ Lognormal(μ, σ), then
        E[X] = exp(μ + σ²/2)
        
        Given cost estimate and variance factor, compute μ and σ.
        
        Args:
            estimate: Expected cost (mode/estimate)
            variance_factor: Coefficient of variation (σ/μ), typically 0.1-0.3
            size: Number of samples
            
        Returns:
            numpy array of sampled costs
        """
        if estimate <= 0:
            raise ValueError("estimate must be positive")
        if variance_factor <= 0 or variance_factor >= 1:
            raise ValueError("variance_factor should be between 0 and 1")
        
        # Lognormal parameterization:
        # CV = sqrt(exp(σ²) - 1) ≈ σ for small σ
        # So σ ≈ variance_factor
        sigma = variance_factor
        
        # E[Lognormal] = exp(μ + σ²/2) = estimate
        # μ = log(estimate) - σ²/2
        mu = np.log(estimate) - 0.5 * sigma**2
        
        return lognorm.rvs(s=sigma, scale=np.exp(mu), size=size)

    @staticmethod
    def sample_pert_cost(min_cost, likely_cost, max_cost, size=1):
        """
        Sample cost using PERT distribution (triangular approximation).
        
        Args:
            min_cost: Minimum cost estimate
            likely_cost: Most likely cost
            max_cost: Maximum cost
            size: Number of samples
            
        Returns:
            numpy array of sampled costs
        """
        return DurationSampler.sample_triangular(min_cost, likely_cost, max_cost, size=size)


class RiskEventSampler:
    """Samples risk event occurrence and impacts."""

    @staticmethod
    def sample_bernoulli(probability, size=1):
        """
        Sample binary event occurrence.
        
        Args:
            probability: Probability of event (0-1)
            size: Number of samples
            
        Returns:
            numpy array of binary outcomes (0 or 1)
        """
        if not 0 <= probability <= 1:
            raise ValueError("probability must be between 0 and 1")
        
        return np.random.binomial(n=1, p=probability, size=size)

    @staticmethod
    def sample_impact_distribution(impact_type, params, size=1):
        """
        Sample impact magnitude from specified distribution.
        
        Args:
            impact_type: 'uniform', 'triangular', 'exponential', 'lognormal'
            params: dict with distribution parameters
            size: Number of samples
            
        Returns:
            numpy array of impact samples
        """
        if impact_type == "uniform":
            low = params.get("low", 0)
            high = params.get("high", 1)
            return np.random.uniform(low, high, size=size)
        
        elif impact_type == "triangular":
            min_val = params.get("min", 0)
            mode_val = params.get("mode", 0.5)
            max_val = params.get("max", 1)
            a = min_val
            b = max_val
            c = (mode_val - a) / (b - a) if b > a else 0.5
            c = np.clip(c, 0, 1)
            return triang.rvs(c, loc=a, scale=b - a, size=size)
        
        elif impact_type == "exponential":
            scale = params.get("scale", 1)
            return np.random.exponential(scale=scale, size=size)
        
        elif impact_type == "lognormal":
            estimate = params.get("estimate", 1)
            cv = params.get("cv", 0.2)
            sigma = cv
            mu = np.log(estimate) - 0.5 * sigma**2
            return lognorm.rvs(s=sigma, scale=np.exp(mu), size=size)
        
        else:
            raise ValueError(f"Unknown impact_type: {impact_type}")


def compute_lognormal_params(mean, std_dev):
    """Compute lognormal parameters (mu, sigma) from mean and std dev.
    
    Given E[X]=mean, compute mu and sigma for Lognormal(mu, sigma).
    Uses CV = std_dev/mean as starting point.
    
    Args:
        mean: Expected value of the lognormal distribution
        std_dev: Standard deviation of the lognormal distribution
        
    Returns:
        tuple: (mu, sigma) parameters for scipy.stats.lognorm
        
    Raises:
        ValueError: if mean is not positive or std_dev is negative
    """
    if mean <= 0 or std_dev < 0:
        raise ValueError("mean must be positive and std_dev must be non-negative")
    
    cv = std_dev / mean  # coefficient of variation
    sigma = np.sqrt(np.log(cv**2 + 1))  # exact relationship
    mu = np.log(mean) - sigma**2 / 2
    return mu, sigma


# Module-level convenience functions for direct import
def sample_triangular(min_val, likely_val, max_val, size=1, random_state=None):
    """Module-level wrapper for triangular sampling."""
    if random_state is not None:
        np.random.seed(random_state)
    return DurationSampler.sample_triangular(min_val, likely_val, max_val, size=size)


def sample_pert(min_val, likely_val, max_val, size=1, alpha=4, random_state=None):
    """Module-level wrapper for PERT sampling."""
    if random_state is not None:
        np.random.seed(random_state)
    return DurationSampler.sample_pert(min_val, likely_val, max_val, size=size, alpha=alpha)


def sample_lognormal(mu, sigma, size=1, random_state=None):
    """Module-level wrapper for lognormal sampling (log-space parametrization)."""
    if random_state is not None:
        np.random.seed(random_state)
    return lognorm.rvs(s=sigma, scale=np.exp(mu), size=size)
