"""
PURPOSE: Format Monte Carlo simulation results and compute risk-adjusted recommendations.

Transforms raw simulation dict output into human-readable format with
success/failure probabilities, percentiles, and GO/CAUTION/NO-GO recommendations.

SRP/DRY: Single responsibility = output formatting and recommendation logic only.
         No simulation, no analysis. Clean dict-in, dict-out interface.
"""

from typing import Dict, Any


class OutputFormatter:
    """Formats Monte Carlo simulation results and generates recommendations."""

    def __init__(self, go_threshold: float = 80.0, caution_threshold: float = 50.0):
        """
        Initialize formatter with thresholds.
        
        Args:
            go_threshold: Success % for GO recommendation (default 80%)
            caution_threshold: Success % for NO-GO threshold (default 50%)
                - GO: success >= go_threshold
                - CAUTION: caution_threshold <= success < go_threshold
                - NO-GO: success < caution_threshold
        """
        self.go_threshold = go_threshold
        self.caution_threshold = caution_threshold

    def format_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format simulation results into human-readable output.
        
        Args:
            results: Dict from MonteCarloSimulation.run() with keys:
                - success_probability: float (0-1)
                - failure_probability: float (0-1)
                - delay_probability: float (0-1)
                - budget_overrun_probability: float (0-1)
                - duration_percentiles: {10: val, 50: val, 90: val}
                - cost_percentiles: {10: val, 50: val, 90: val}
                - recommendation: str (auto-generated if not present)
        
        Returns:
            Dict with formatted outputs:
                - recommendation: "GO" | "CAUTION" | "NO-GO"
                - success_probability_pct: float (0-100)
                - summary: str (one-line summary)
                - full_report: dict with detailed outputs
        """
        # Extract raw values from simulation output
        success_prob_01 = results.get('success_probability', 0.0)  # 0-1 range
        success_prob_pct = success_prob_01 * 100.0  # Convert to 0-100 range
        
        failure_prob_pct = results.get('failure_probability', 0.0) * 100.0
        delay_prob_pct = results.get('delay_probability', 0.0) * 100.0
        budget_overrun_pct = results.get('budget_overrun_probability', 0.0) * 100.0
        
        duration_pcts = results.get('duration_percentiles', {10: 0, 50: 0, 90: 0})
        cost_pcts = results.get('cost_percentiles', {10: 0, 50: 0, 90: 0})
        
        # Compute recommendation based on success probability
        recommendation = self._compute_recommendation(success_prob_pct)
        
        # Build summary
        summary = (
            f"Recommendation: {recommendation}. "
            f"Success probability: {success_prob_pct:.1f}%. "
            f"P50 duration: {duration_pcts.get(50, 0):.1f} days, "
            f"P50 cost: ${cost_pcts.get(50, 0):,.0f}."
        )
        
        # Return formatted results
        return {
            'recommendation': recommendation,
            'success_probability_pct': success_prob_pct,
            'failure_probability_pct': failure_prob_pct,
            'delay_probability_pct': delay_prob_pct,
            'budget_overrun_probability_pct': budget_overrun_pct,
            'summary': summary,
            'duration_percentiles': duration_pcts,
            'cost_percentiles': cost_pcts,
            'full_report': {
                'recommendation': recommendation,
                'probabilities': {
                    'success': success_prob_pct,
                    'failure': failure_prob_pct,
                    'delay': delay_prob_pct,
                    'budget_overrun': budget_overrun_pct,
                },
                'percentiles': {
                    'duration': duration_pcts,
                    'cost': cost_pcts,
                }
            }
        }

    def _compute_recommendation(self, success_probability_pct: float) -> str:
        """
        Compute GO/CAUTION/NO-GO recommendation based on success probability.
        
        Args:
            success_probability_pct: Success probability as percentage (0-100)
        
        Returns:
            "GO" | "CAUTION" | "NO-GO"
        """
        if success_probability_pct >= self.go_threshold:
            return "GO"
        elif success_probability_pct >= self.caution_threshold:
            return "CAUTION"
        else:
            return "NO-GO"
