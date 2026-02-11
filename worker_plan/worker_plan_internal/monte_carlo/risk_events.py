"""
Risk event sampling for Monte Carlo simulation.

PURPOSE:
    Model discrete risk events as Bernoulli trials with defined impact
    distributions. A risk event occurs with a given probability and, when it
    occurs, causes an impact drawn from a specified distribution.

RESPONSIBILITIES:
    - Sample Bernoulli trials (did event occur or not?)
    - Sample impact magnitudes from distributions (triangular, lognormal, etc.)
    - Combine occurrence and impact for scenario evaluation
    - NO simulation aggregation, NO probability calculation

SRP/DRY CHECK:
    Single responsibility: risk event sampling. Functions are pure samplers
    with no side effects or state.
"""

import numpy as np
from scipy import stats
from typing import Union, Optional, Callable, Literal
from worker_plan_internal.monte_carlo.distributions import (
    sample_triangular,
    sample_lognormal,
)


def sample_bernoulli_impact(
    probability: float,
    impact_fn: Callable[[], float],
    size: int = 1,
    random_state: Union[int, np.random.RandomState, None] = None,
) -> Union[float, np.ndarray]:
    """
    Sample Bernoulli occurrence + impact distribution for a risk event.

    This function combines two steps:
    1. Bernoulli trial: does the event occur? (probability p)
    2. If occurs: sample impact magnitude from impact_fn

    If the event does not occur, impact is zero.

    Args:
        probability: Probability of event occurring (0 to 1)
        impact_fn: Callable that returns impact value (e.g., lambda: sample_triangular(...))
        size: Number of samples (default 1)
        random_state: Seed for reproducibility

    Returns:
        float or ndarray: Impact value(s). Zero if event didn't occur, positive if it did.

    Raises:
        ValueError: If probability not in [0, 1]
        TypeError: If impact_fn is not callable
    """
    # Validate inputs
    if not 0 <= probability <= 1:
        raise ValueError(f"probability must be in [0, 1], got {probability}")

    if not callable(impact_fn):
        raise TypeError(f"impact_fn must be callable, got {type(impact_fn)}")

    rng = np.random.RandomState(random_state)

    # Sample Bernoulli occurrences
    occurrences = rng.binomial(n=1, p=probability, size=size)

    # For each occurrence, compute impact (0 if didn't occur)
    if size == 1:
        if occurrences[0] == 1:
            return impact_fn()
        else:
            return 0.0
    else:
        # Vectorized: sample impacts for occurrences=1, set rest to 0
        impacts = np.zeros(size)
        num_events = np.sum(occurrences)

        if num_events > 0:
            # Sample impacts for all occurrences (we'll zero them out if not needed)
            sampled_impacts = np.array(
                [impact_fn() for _ in range(int(num_events))]
            )

            # Assign sampled impacts to positions where occurrence=1
            event_positions = np.where(occurrences == 1)[0]
            impacts[event_positions] = sampled_impacts

        return impacts


def sample_risk_event(
    probability: float,
    impact_min: float,
    impact_max: float,
    impact_mode: Optional[float] = None,
    impact_distribution: Literal["triangular", "lognormal"] = "triangular",
    mu: Optional[float] = None,
    sigma: Optional[float] = None,
    size: int = 1,
    random_state: Union[int, np.random.RandomState, None] = None,
) -> Union[float, np.ndarray]:
    """
    Sample a complete risk event: occurrence probability + impact distribution.

    This is a convenience wrapper around sample_bernoulli_impact for common
    scenarios. It supports triangular (3-point) and lognormal (mean/std) impacts.

    Args:
        probability: Probability of event occurring (0 to 1)
        impact_min: Minimum impact if event occurs
        impact_max: Maximum impact if event occurs
        impact_mode: Mode/likely value for triangular impact (required for triangular)
        impact_distribution: "triangular" or "lognormal"
        mu: Mean of log(impact) for lognormal (overrides impact_min if provided)
        sigma: Std dev of log(impact) for lognormal
        size: Number of samples (default 1)
        random_state: Seed for reproducibility

    Returns:
        float or ndarray: Impact value(s)

    Raises:
        ValueError: If parameters don't make sense for chosen distribution
    """
    # Validate probability
    if not 0 <= probability <= 1:
        raise ValueError(f"probability must be in [0, 1], got {probability}")

    if impact_distribution == "triangular":
        # Validate triangular parameters
        if impact_mode is None:
            raise ValueError(
                "impact_mode required for triangular impact distribution"
            )
        if not (impact_min <= impact_mode <= impact_max):
            raise ValueError(
                f"Invalid triangular params: min={impact_min}, mode={impact_mode}, max={impact_max}"
            )

        # Create impact sampler for triangular
        def impact_fn():
            return sample_triangular(impact_min, impact_mode, impact_max)

    elif impact_distribution == "lognormal":
        # For lognormal, use mu/sigma if provided, otherwise compute from min/max
        if mu is None or sigma is None:
            if impact_min <= 0 or impact_max <= 0:
                raise ValueError(
                    f"impact_min and impact_max must be positive for lognormal, "
                    f"got min={impact_min}, max={impact_max}"
                )
            # Use impact_min as rough mean estimate for parameter computation
            # (for proper calibration, pass explicit mu/sigma)
            from worker_plan_internal.monte_carlo.distributions import (
                compute_lognormal_params,
            )

            mean_estimate = (impact_min + impact_max) / 2
            std_estimate = (impact_max - impact_min) / 4  # Rough heuristic
            mu, sigma = compute_lognormal_params(mean_estimate, std_estimate)

        def impact_fn():
            return sample_lognormal(mu, sigma)

    else:
        raise ValueError(
            f"Unknown impact_distribution: {impact_distribution}. "
            f"Must be 'triangular' or 'lognormal'"
        )

    # Delegate to Bernoulli+impact sampler
    return sample_bernoulli_impact(
        probability, impact_fn, size=size, random_state=random_state
    )


def sample_portfolio_risk(
    risk_events: list,
    size: int = 1,
    random_state: Union[int, np.random.RandomState, None] = None,
) -> np.ndarray:
    """
    Sample multiple independent risk events and sum their impacts.

    Args:
        risk_events: List of dicts with keys:
            - 'probability': float in [0, 1]
            - 'impact_fn': callable returning impact
            Additional keys depend on the implementation
        size: Number of scenarios
        random_state: Seed for reproducibility

    Returns:
        ndarray: Total impact across all events for each scenario (shape: (size,))
    """
    if not risk_events:
        return np.zeros(size)

    # Sample each risk event independently
    impacts_per_event = []
    for event in risk_events:
        probability = event["probability"]
        impact_fn = event["impact_fn"]

        samples = sample_bernoulli_impact(
            probability, impact_fn, size=size, random_state=random_state
        )
        impacts_per_event.append(
            samples if isinstance(samples, np.ndarray) else np.array([samples])
        )

    # Sum impacts across all events
    total_impacts = np.sum(impacts_per_event, axis=0)

    return total_impacts
