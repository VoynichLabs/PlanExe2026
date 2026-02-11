"""
Monte Carlo simulation module for plan success probability estimation.

PURPOSE:
    Provide statistically rigorous uncertainty quantification for project planning
    by running 10,000+ independent scenarios with properly specified distributions
    for task durations, costs, and risk events.

RESPONSIBILITIES:
    - Expose distribution samplers (triangular, PERT, lognormal)
    - Provide Bernoulli risk event sampling
    - Format simulation results with risk-adjusted recommendations
    - Compute variance-based sensitivity analysis

SRP/DRY CHECK:
    Each submodule has a single responsibility:
    - distributions.py: Sampling from uncertainty distributions only
    - risk_events.py: Bernoulli + impact sampling only
    - simulation.py: 10K scenario aggregation only
    - outputs.py: Result formatting and recommendations only
    - sensitivity.py: Sensitivity analysis only
"""

from .outputs import OutputFormatter, MonteCarloResults
from .sensitivity import SensitivityAnalyzer, SensitivityDriver

__version__ = "0.1.0"
__author__ = "PlanExe Team"

__all__ = [
    "sample_triangular",
    "sample_pert",
    "sample_lognormal",
    "sample_risk_event",
    "sample_bernoulli_impact",
    "OutputFormatter",
    "MonteCarloResults",
    "SensitivityAnalyzer",
    "SensitivityDriver",
]
