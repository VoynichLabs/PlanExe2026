"""
PURPOSE: Unit tests for outputs.py module.

Tests cover:
1. Result formatting with valid mock data
2. Recommendation thresholds (GO/CAUTION/NO-GO)
3. Narrative generation accuracy
4. Error handling for invalid inputs
5. Serialization to JSON-compatible dicts
"""

import pytest
from worker_plan_internal.monte_carlo.outputs import (
    OutputFormatter,
    MonteCarloResults,
)


class TestMonteCarloResults:
    """Tests for MonteCarloResults dataclass."""

    def test_monte_carlo_results_creation(self):
        """Test basic creation and field assignment."""
        result = MonteCarloResults(
            success_probability=85.5,
            failure_probability=14.5,
            risk_adjusted_recommendation="GO",
            duration_p10=10.0,
            duration_p50=15.0,
            duration_p90=25.0,
            cost_p10=1000.0,
            cost_p50=1500.0,
            cost_p90=2500.0,
            summary_narrative="Test narrative.",
            percentiles_dict={
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        )
        assert result.success_probability == 85.5
        assert result.failure_probability == 14.5
        assert result.risk_adjusted_recommendation == "GO"
        assert result.duration_p50 == 15.0
        assert result.cost_p90 == 2500.0

    def test_to_dict_serialization(self):
        """Test conversion to JSON-compatible dict."""
        result = MonteCarloResults(
            success_probability=75.0,
            failure_probability=25.0,
            risk_adjusted_recommendation="CAUTION",
            duration_p10=10.5,
            duration_p50=15.5,
            duration_p90=25.5,
            cost_p10=1000.5,
            cost_p50=1500.5,
            cost_p90=2500.5,
            summary_narrative="Test narrative.",
            percentiles_dict={
                "duration": {"p10": 10.5, "p50": 15.5, "p90": 25.5},
                "cost": {"p10": 1000.5, "p50": 1500.5, "p90": 2500.5},
            },
        )
        result_dict = result.to_dict()
        assert result_dict["success_probability"] == 75.0
        assert result_dict["risk_adjusted_recommendation"] == "CAUTION"
        assert result_dict["duration"]["p50"] == 15.5
        assert result_dict["cost"]["p10"] == 1000.5
        assert isinstance(result_dict, dict)


class TestOutputFormatterComputeRecommendation:
    """Tests for _compute_recommendation method."""

    def test_go_recommendation_at_threshold(self):
        """Test GO when success_prob equals GO_THRESHOLD (80%)."""
        result = OutputFormatter._compute_recommendation(
            success_prob=80.0,
            go_threshold=80.0,
            caution_min=50.0,
            caution_max=80.0,
        )
        assert result == "GO"

    def test_go_recommendation_above_threshold(self):
        """Test GO when success_prob > GO_THRESHOLD."""
        result = OutputFormatter._compute_recommendation(
            success_prob=90.0,
            go_threshold=80.0,
            caution_min=50.0,
            caution_max=80.0,
        )
        assert result == "GO"

    def test_caution_recommendation_at_lower_bound(self):
        """Test CAUTION when success_prob equals CAUTION_MIN_THRESHOLD (50%)."""
        result = OutputFormatter._compute_recommendation(
            success_prob=50.0,
            go_threshold=80.0,
            caution_min=50.0,
            caution_max=80.0,
        )
        assert result == "CAUTION"

    def test_caution_recommendation_at_upper_bound(self):
        """Test CAUTION when success_prob < GO_THRESHOLD (just below 80%)."""
        result = OutputFormatter._compute_recommendation(
            success_prob=79.9,
            go_threshold=80.0,
            caution_min=50.0,
            caution_max=80.0,
        )
        assert result == "CAUTION"

    def test_caution_recommendation_midrange(self):
        """Test CAUTION in middle of range (65%)."""
        result = OutputFormatter._compute_recommendation(
            success_prob=65.0,
            go_threshold=80.0,
            caution_min=50.0,
            caution_max=80.0,
        )
        assert result == "CAUTION"

    def test_nogo_recommendation_at_threshold(self):
        """Test NO-GO when success_prob just below CAUTION_MIN (49.9%)."""
        result = OutputFormatter._compute_recommendation(
            success_prob=49.9,
            go_threshold=80.0,
            caution_min=50.0,
            caution_max=80.0,
        )
        assert result == "NO-GO"

    def test_nogo_recommendation_very_low(self):
        """Test NO-GO for very low success probability (10%)."""
        result = OutputFormatter._compute_recommendation(
            success_prob=10.0,
            go_threshold=80.0,
            caution_min=50.0,
            caution_max=80.0,
        )
        assert result == "NO-GO"

    def test_nogo_recommendation_zero(self):
        """Test NO-GO for zero success probability."""
        result = OutputFormatter._compute_recommendation(
            success_prob=0.0,
            go_threshold=80.0,
            caution_min=50.0,
            caution_max=80.0,
        )
        assert result == "NO-GO"

    def test_custom_thresholds(self):
        """Test with custom threshold values."""
        result = OutputFormatter._compute_recommendation(
            success_prob=75.0,
            go_threshold=90.0,
            caution_min=60.0,
            caution_max=90.0,
        )
        assert result == "CAUTION"


class TestOutputFormatterGenerateNarrative:
    """Tests for _generate_narrative method."""

    def test_narrative_go(self):
        """Test narrative generation for GO recommendation."""
        narrative = OutputFormatter._generate_narrative(
            success_prob=85.0,
            failure_prob=15.0,
            median_duration=20.0,
            median_cost=5000.0,
            recommendation="GO",
        )
        assert "85.0%" in narrative
        assert "15.0%" in narrative
        assert "20.0" in narrative
        assert "5000.00" in narrative
        assert "GO" in narrative
        assert "high probability of success" in narrative
        assert "Proceed" in narrative

    def test_narrative_caution(self):
        """Test narrative generation for CAUTION recommendation."""
        narrative = OutputFormatter._generate_narrative(
            success_prob=65.0,
            failure_prob=35.0,
            median_duration=25.0,
            median_cost=6000.0,
            recommendation="CAUTION",
        )
        assert "65.0%" in narrative
        assert "35.0%" in narrative
        assert "25.0" in narrative
        assert "6000.00" in narrative
        assert "CAUTION" in narrative
        assert "moderate probability" in narrative
        assert "Mitigate" in narrative

    def test_narrative_nogo(self):
        """Test narrative generation for NO-GO recommendation."""
        narrative = OutputFormatter._generate_narrative(
            success_prob=40.0,
            failure_prob=60.0,
            median_duration=30.0,
            median_cost=8000.0,
            recommendation="NO-GO",
        )
        assert "40.0%" in narrative
        assert "60.0%" in narrative
        assert "30.0" in narrative
        assert "8000.00" in narrative
        assert "NO-GO" in narrative
        assert "low probability" in narrative
        assert "re-scop" in narrative


class TestOutputFormatterFormatResults:
    """Tests for format_results method."""

    def test_format_results_valid_go(self):
        """Test formatting valid results with GO recommendation."""
        mock_results = {
            "probabilities": {"success": 85.0, "failure": 15.0},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        output = OutputFormatter.format_results(mock_results)
        assert output.success_probability == 85.0
        assert output.failure_probability == 15.0
        assert output.risk_adjusted_recommendation == "GO"
        assert output.duration_p50 == 15.0
        assert output.cost_p90 == 2500.0
        assert isinstance(output.summary_narrative, str)
        assert len(output.summary_narrative) > 0

    def test_format_results_valid_caution(self):
        """Test formatting valid results with CAUTION recommendation."""
        mock_results = {
            "probabilities": {"success": 65.0, "failure": 35.0},
            "percentiles": {
                "duration": {"p10": 12.0, "p50": 18.0, "p90": 30.0},
                "cost": {"p10": 1200.0, "p50": 1800.0, "p90": 3000.0},
            },
        }
        output = OutputFormatter.format_results(mock_results)
        assert output.success_probability == 65.0
        assert output.failure_probability == 35.0
        assert output.risk_adjusted_recommendation == "CAUTION"

    def test_format_results_valid_nogo(self):
        """Test formatting valid results with NO-GO recommendation."""
        mock_results = {
            "probabilities": {"success": 35.0, "failure": 65.0},
            "percentiles": {
                "duration": {"p10": 15.0, "p50": 25.0, "p90": 40.0},
                "cost": {"p10": 1500.0, "p50": 2500.0, "p90": 4000.0},
            },
        }
        output = OutputFormatter.format_results(mock_results)
        assert output.success_probability == 35.0
        assert output.failure_probability == 65.0
        assert output.risk_adjusted_recommendation == "NO-GO"

    def test_format_results_invalid_success_prob_high(self):
        """Test error when success_probability > 100."""
        mock_results = {
            "probabilities": {"success": 105.0, "failure": -5.0},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        with pytest.raises(ValueError):
            OutputFormatter.format_results(mock_results)

    def test_format_results_invalid_success_prob_negative(self):
        """Test error when success_probability < 0."""
        mock_results = {
            "probabilities": {"success": -10.0, "failure": 110.0},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        with pytest.raises(ValueError):
            OutputFormatter.format_results(mock_results)

    def test_format_results_invalid_failure_prob_high(self):
        """Test error when failure_probability > 100."""
        mock_results = {
            "probabilities": {"success": 50.0, "failure": 150.0},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        with pytest.raises(ValueError):
            OutputFormatter.format_results(mock_results)

    def test_format_results_missing_keys(self):
        """Test handling of missing percentile keys."""
        mock_results = {
            "probabilities": {"success": 75.0, "failure": 25.0},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0},  # missing p90
                "cost": {},
            },
        }
        output = OutputFormatter.format_results(mock_results)
        assert output.success_probability == 75.0
        assert output.duration_p90 == 0.0  # default
        assert output.cost_p10 == 0.0  # default

    def test_format_results_empty_percentiles(self):
        """Test handling of empty percentiles dict."""
        mock_results = {
            "probabilities": {"success": 70.0, "failure": 30.0},
            "percentiles": {},
        }
        output = OutputFormatter.format_results(mock_results)
        assert output.success_probability == 70.0
        assert output.duration_p10 == 0.0
        assert output.cost_p50 == 0.0

    def test_format_results_custom_thresholds(self):
        """Test format_results with custom thresholds."""
        mock_results = {
            "probabilities": {"success": 85.0, "failure": 15.0},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        # With custom thresholds: GO at 90%
        output = OutputFormatter.format_results(
            mock_results, go_threshold=90.0, caution_min=70.0, caution_max=90.0
        )
        assert output.risk_adjusted_recommendation == "CAUTION"  # 85% < 90%

    def test_format_results_result_structure(self):
        """Test that result has all expected attributes."""
        mock_results = {
            "probabilities": {"success": 80.0, "failure": 20.0},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        output = OutputFormatter.format_results(mock_results)
        assert hasattr(output, "success_probability")
        assert hasattr(output, "failure_probability")
        assert hasattr(output, "risk_adjusted_recommendation")
        assert hasattr(output, "duration_p10")
        assert hasattr(output, "duration_p50")
        assert hasattr(output, "duration_p90")
        assert hasattr(output, "cost_p10")
        assert hasattr(output, "cost_p50")
        assert hasattr(output, "cost_p90")
        assert hasattr(output, "summary_narrative")
        assert hasattr(output, "percentiles_dict")

    def test_format_results_serialization_roundtrip(self):
        """Test that to_dict() produces valid structure."""
        mock_results = {
            "probabilities": {"success": 75.0, "failure": 25.0},
            "percentiles": {
                "duration": {"p10": 11.5, "p50": 16.5, "p90": 26.5},
                "cost": {"p10": 1100.5, "p50": 1600.5, "p90": 2600.5},
            },
        }
        output = OutputFormatter.format_results(mock_results)
        result_dict = output.to_dict()
        
        # Verify structure
        assert "success_probability" in result_dict
        assert "failure_probability" in result_dict
        assert "risk_adjusted_recommendation" in result_dict
        assert "duration" in result_dict
        assert "cost" in result_dict
        assert "summary_narrative" in result_dict
        assert "percentiles_dict" in result_dict
        
        # Verify types
        assert isinstance(result_dict["success_probability"], float)
        assert isinstance(result_dict["duration"], dict)
        assert isinstance(result_dict["cost"], dict)

    def test_format_results_boundary_at_80(self):
        """Test GO/CAUTION boundary at exactly 80%."""
        results_80 = {
            "probabilities": {"success": 80.0, "failure": 20.0},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        output_80 = OutputFormatter.format_results(results_80)
        assert output_80.risk_adjusted_recommendation == "GO"

        results_79_9 = {
            "probabilities": {"success": 79.9, "failure": 20.1},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        output_79_9 = OutputFormatter.format_results(results_79_9)
        assert output_79_9.risk_adjusted_recommendation == "CAUTION"

    def test_format_results_boundary_at_50(self):
        """Test CAUTION/NO-GO boundary at exactly 50%."""
        results_50 = {
            "probabilities": {"success": 50.0, "failure": 50.0},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        output_50 = OutputFormatter.format_results(results_50)
        assert output_50.risk_adjusted_recommendation == "CAUTION"

        results_49_9 = {
            "probabilities": {"success": 49.9, "failure": 50.1},
            "percentiles": {
                "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
                "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
            },
        }
        output_49_9 = OutputFormatter.format_results(results_49_9)
        assert output_49_9.risk_adjusted_recommendation == "NO-GO"


class TestIntegrationOutputs:
    """Integration tests for realistic output scenarios."""

    def test_realistic_low_risk_project(self):
        """Test realistic low-risk project scenario."""
        mock_results = {
            "probabilities": {"success": 92.5, "failure": 7.5},
            "percentiles": {
                "duration": {"p10": 45.0, "p50": 52.0, "p90": 65.0},
                "cost": {"p10": 48000.0, "p50": 55000.0, "p90": 68000.0},
            },
        }
        output = OutputFormatter.format_results(mock_results)
        assert output.risk_adjusted_recommendation == "GO"
        assert "high probability" in output.summary_narrative

    def test_realistic_medium_risk_project(self):
        """Test realistic medium-risk project scenario."""
        mock_results = {
            "probabilities": {"success": 62.3, "failure": 37.7},
            "percentiles": {
                "duration": {"p10": 55.0, "p50": 75.0, "p90": 110.0},
                "cost": {"p10": 50000.0, "p50": 70000.0, "p90": 110000.0},
            },
        }
        output = OutputFormatter.format_results(mock_results)
        assert output.risk_adjusted_recommendation == "CAUTION"
        assert "moderate" in output.summary_narrative

    def test_realistic_high_risk_project(self):
        """Test realistic high-risk project scenario."""
        mock_results = {
            "probabilities": {"success": 28.5, "failure": 71.5},
            "percentiles": {
                "duration": {"p10": 80.0, "p50": 150.0, "p90": 250.0},
                "cost": {"p10": 100000.0, "p50": 200000.0, "p90": 400000.0},
            },
        }
        output = OutputFormatter.format_results(mock_results)
        assert output.risk_adjusted_recommendation == "NO-GO"
        assert "low probability" in output.summary_narrative
        assert "re-scop" in output.summary_narrative


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
