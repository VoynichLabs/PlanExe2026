"""
PURPOSE: Simulation configuration and threshold parameters for Monte Carlo engine.

RESPONSIBILITIES:
- Define simulation hyperparameters (number of runs, random seed)
- Success/failure threshold definitions
- Risk tolerance and recommendation logic parameters
- Single responsibility: configuration only, no simulation logic
"""

# Simulation Parameters
NUM_RUNS = 10000  # Standard Monte Carlo sample size
RANDOM_SEED = None  # Set to int for reproducibility, None for random

# Success/Failure Thresholds
# A scenario is marked as successful if ALL conditions are met:
SUCCESS_DEADLINE_BUFFER_DAYS = 0  # Must complete by deadline + buffer
SUCCESS_BUDGET_TOLERANCE = 1.0  # Budget must not exceed estimate * tolerance (1.0 = no overrun)
SUCCESS_CRITICAL_RISK_LIMIT = 0.0  # Number of critical risks allowed (typically 0)

# Probability Thresholds for Recommendations
GO_THRESHOLD = 0.80  # P(success) >= 80% → GO
NO_GO_THRESHOLD = 0.50  # P(success) < 50% → NO-GO
RE_SCOPE_THRESHOLD = 0.65  # 50% <= P(success) < 80% → RE-SCOPE

# Percentile Outputs
PERCENTILES = [10, 50, 90]  # P10, P50, P90

# Risk Analysis
RISK_EVENT_DEFAULT_PROBABILITY = 0.1  # Default probability for unspecified risks
RISK_EVENT_DEFAULT_IMPACT_TYPE = "triangular"  # Default impact distribution

# Sensitivity Analysis (Tornado Chart)
TOP_N_DRIVERS = 5  # Number of top uncertainty drivers to report

# Output Configuration
ROUND_PROBABILITY = 3  # Decimal places for probabilities
ROUND_DURATION = 1  # Decimal places for durations
ROUND_COST = 2  # Decimal places for costs


def get_success_thresholds():
    """Return threshold configuration for success/failure determination."""
    return {
        "deadline_buffer_days": SUCCESS_DEADLINE_BUFFER_DAYS,
        "budget_tolerance": SUCCESS_BUDGET_TOLERANCE,
        "critical_risk_limit": SUCCESS_CRITICAL_RISK_LIMIT,
    }


def get_recommendation_thresholds():
    """Return thresholds for go/no-go/re-scope recommendations."""
    return {
        "go": GO_THRESHOLD,
        "no_go": NO_GO_THRESHOLD,
        "re_scope": RE_SCOPE_THRESHOLD,
    }
