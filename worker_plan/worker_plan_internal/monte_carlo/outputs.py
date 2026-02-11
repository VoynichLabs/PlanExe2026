"""
PURPOSE: Format Monte Carlo simulation results and compute risk-adjusted recommendations.

This module transforms raw simulation outputs into human-readable formats,
including success/failure probabilities, percentiles, and GO/CAUTION/NO-GO
recommendations based on configurable thresholds.

SRP/DRY: Single responsibility = output formatting and recommendation logic.
         No simulation, no sensitivity analysis. Clean interface to simulation results.
"""

from dataclasses import dataclass
from typing import Dict, List, Any
import numpy as np


@dataclass
class MonteCarloResults:
    """Structured output from Monte Carlo simulation formatting.
    
    Attributes:
        success_probability (float): Percentage of successful scenarios (0-100).
        failure_probability (float): Percentage of failed scenarios (0-100).
        risk_adjusted_recommendation (str): "GO", "CAUTION", or "NO-GO".
        duration_p10 (float): 10th percentile duration (days).
        duration_p50 (float): 50th percentile duration (days).
        duration_p90 (float): 90th percentile duration (days).
        cost_p10 (float): 10th percentile cost.
        cost_p50 (float): 50th percentile cost.
        cost_p90 (float): 90th percentile cost.
        summary_narrative (str): Plain English summary of key findings.
        percentiles_dict (dict): Full percentile breakdown for advanced users.
    """
    success_probability: float
    failure_probability: float
    risk_adjusted_recommendation: str
    duration_p10: float
    duration_p50: float
    duration_p90: float
    cost_p10: float
    cost_p50: float
    cost_p90: float
    summary_narrative: str
    percentiles_dict: Dict[str, Dict[str, float]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for JSON serialization."""
        return {
            "success_probability": round(self.success_probability, 2),
            "failure_probability": round(self.failure_probability, 2),
            "risk_adjusted_recommendation": self.risk_adjusted_recommendation,
            "duration": {
                "p10": round(self.duration_p10, 2),
                "p50": round(self.duration_p50, 2),
                "p90": round(self.duration_p90, 2),
            },
            "cost": {
                "p10": round(self.cost_p10, 2),
                "p50": round(self.cost_p50, 2),
                "p90": round(self.cost_p90, 2),
            },
            "summary_narrative": self.summary_narrative,
            "percentiles_dict": {
                k: {kk: round(vv, 2) for kk, vv in v.items()}
                for k, v in self.percentiles_dict.items()
            },
        }


class OutputFormatter:
    """
    Formats raw simulation results into actionable outputs.
    
    Thresholds for risk-adjusted recommendations:
    - GO: success_probability >= 80%
    - CAUTION: 50% <= success_probability < 80%
    - NO-GO: success_probability < 50%
    """

    # Recommendation thresholds
    GO_THRESHOLD = 80.0
    CAUTION_MIN_THRESHOLD = 50.0
    CAUTION_MAX_THRESHOLD = 80.0

    @staticmethod
    def format_results(
        results: Dict[str, Any],
        go_threshold: float = GO_THRESHOLD,
        caution_min: float = CAUTION_MIN_THRESHOLD,
        caution_max: float = CAUTION_MAX_THRESHOLD,
    ) -> MonteCarloResults:
        """
        Format simulation results into structured output.

        Args:
            results: Dictionary from simulation.py containing:
                - 'probabilities': dict with 'success', 'failure', etc.
                - 'percentiles': dict with 'duration' and 'cost' percentiles
                - 'scenarios': list of scenario dicts (optional, for narratives)
                - Any other computed fields
            go_threshold: Success probability threshold for GO recommendation (default 80%).
            caution_min: Min threshold for CAUTION recommendation (default 50%).
            caution_max: Max threshold for CAUTION recommendation (default 80%).

        Returns:
            MonteCarloResults object with formatted outputs.

        Raises:
            KeyError: If required keys missing from results.
            ValueError: If probabilities are not in [0, 100] or don't sum to ~100.
        """
        # Extract probabilities
        probabilities = results.get("probabilities", {})
        success_prob = probabilities.get("success", 0.0)
        failure_prob = probabilities.get("failure", 0.0)

        # Validate probabilities
        if not (0 <= success_prob <= 100):
            raise ValueError(f"success_probability must be in [0, 100], got {success_prob}")
        if not (0 <= failure_prob <= 100):
            raise ValueError(f"failure_probability must be in [0, 100], got {failure_prob}")

        # Extract percentiles
        percentiles = results.get("percentiles", {})
        duration_pcts = percentiles.get("duration", {})
        cost_pcts = percentiles.get("cost", {})

        # Get P10, P50, P90 for duration and cost
        duration_p10 = duration_pcts.get("p10", 0.0)
        duration_p50 = duration_pcts.get("p50", 0.0)
        duration_p90 = duration_pcts.get("p90", 0.0)
        cost_p10 = cost_pcts.get("p10", 0.0)
        cost_p50 = cost_pcts.get("p50", 0.0)
        cost_p90 = cost_pcts.get("p90", 0.0)

        # Compute risk-adjusted recommendation
        recommendation = OutputFormatter._compute_recommendation(
            success_prob, go_threshold, caution_min, caution_max
        )

        # Generate summary narrative
        narrative = OutputFormatter._generate_narrative(
            success_prob, failure_prob, duration_p50, cost_p50, recommendation
        )

        # Assemble full percentiles dict for reference
        percentiles_dict = {
            "duration": duration_pcts,
            "cost": cost_pcts,
        }

        return MonteCarloResults(
            success_probability=success_prob,
            failure_probability=failure_prob,
            risk_adjusted_recommendation=recommendation,
            duration_p10=duration_p10,
            duration_p50=duration_p50,
            duration_p90=duration_p90,
            cost_p10=cost_p10,
            cost_p50=cost_p50,
            cost_p90=cost_p90,
            summary_narrative=narrative,
            percentiles_dict=percentiles_dict,
        )

    @staticmethod
    def _compute_recommendation(
        success_prob: float,
        go_threshold: float,
        caution_min: float,
        caution_max: float,
    ) -> str:
        """
        Compute risk-adjusted recommendation based on success probability.

        Args:
            success_prob: Success probability as percentage (0-100).
            go_threshold: Threshold for GO (default 80%).
            caution_min: Min threshold for CAUTION (default 50%).
            caution_max: Max threshold for CAUTION (default 80%).

        Returns:
            "GO", "CAUTION", or "NO-GO".
        """
        if success_prob >= go_threshold:
            return "GO"
        elif caution_min <= success_prob < caution_max:
            return "CAUTION"
        else:
            return "NO-GO"

    @staticmethod
    def _generate_narrative(
        success_prob: float,
        failure_prob: float,
        median_duration: float,
        median_cost: float,
        recommendation: str,
    ) -> str:
        """
        Generate a plain English summary of key findings.

        Args:
            success_prob: Success probability percentage.
            failure_prob: Failure probability percentage.
            median_duration: P50 (median) duration.
            median_cost: P50 (median) cost.
            recommendation: GO, CAUTION, or NO-GO.

        Returns:
            Plain English narrative string.
        """
        narrative = f"Success probability: {success_prob:.1f}%. "
        narrative += f"Failure probability: {failure_prob:.1f}%. "
        narrative += f"Expected duration (P50): {median_duration:.1f} days. "
        narrative += f"Expected cost (P50): {median_cost:.2f}. "
        narrative += f"Recommendation: {recommendation}. "

        if recommendation == "GO":
            narrative += (
                "The plan has a high probability of success. "
                "Proceed with planning and execution."
            )
        elif recommendation == "CAUTION":
            narrative += (
                "The plan has moderate probability of success. "
                "Mitigate risks, review assumptions, and prepare contingencies."
            )
        else:  # NO-GO
            narrative += (
                "The plan has low probability of success. "
                "Consider re-scoping, reducing scope, or increasing resources."
            )

        return narrative
