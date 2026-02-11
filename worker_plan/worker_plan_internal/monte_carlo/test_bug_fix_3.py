"""
Test for Bug Fix #3: Type mismatch in outputs.py recommendation thresholds

Tests that OutputFormatter can safely handle thresholds from config.py
with defensive type checking and conversion.
"""

import sys
import os

# Handle both direct script execution and package imports
if __name__ == "__main__":
    # When run as a script, use absolute imports
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import outputs
    import config
    OutputFormatter = outputs.OutputFormatter
else:
    # When imported as a package
    from outputs import OutputFormatter
    import config


def test_safe_extract_threshold_scalar():
    """Test extraction of scalar threshold values."""
    # Test with float
    result = OutputFormatter._safe_extract_threshold(0.8, 0.5)
    assert result == 0.8, f"Expected 0.8, got {result}"
    
    # Test with int
    result = OutputFormatter._safe_extract_threshold(80, 50)
    assert result == 80.0, f"Expected 80.0, got {result}"
    
    print("✓ Scalar extraction works")


def test_safe_extract_threshold_dict():
    """Test extraction from dict values."""
    # Test with 'value' key
    result = OutputFormatter._safe_extract_threshold({'value': 0.8}, 0.5)
    assert result == 0.8, f"Expected 0.8, got {result}"
    
    # Test with 'threshold' key
    result = OutputFormatter._safe_extract_threshold({'threshold': 0.5}, 0.3)
    assert result == 0.5, f"Expected 0.5, got {result}"
    
    print("✓ Dict extraction works")


def test_safe_extract_threshold_fallback():
    """Test fallback when value is malformed."""
    # Test with None
    result = OutputFormatter._safe_extract_threshold(None, 0.8)
    assert result == 0.8, f"Expected fallback 0.8, got {result}"
    
    # Test with empty dict
    result = OutputFormatter._safe_extract_threshold({}, 0.5)
    assert result == 0.5, f"Expected fallback 0.5, got {result}"
    
    # Test with bad dict
    result = OutputFormatter._safe_extract_threshold({'bad_key': 'bad_value'}, 0.7)
    assert result == 0.7, f"Expected fallback 0.7, got {result}"
    
    print("✓ Fallback handling works")


def test_load_thresholds_from_config():
    """Test loading thresholds from config with conversion."""
    go, no_go, re_scope = OutputFormatter._load_thresholds_from_config()
    
    # Should convert from decimals (0.80, 0.50) to percentages (80.0, 50.0)
    assert go == 80.0, f"Expected GO=80.0, got {go}"
    assert no_go == 50.0, f"Expected NO_GO=50.0, got {no_go}"
    assert re_scope == 65.0, f"Expected RE_SCOPE=65.0, got {re_scope}"
    
    print(f"✓ Config loading works: GO={go}, NO_GO={no_go}, RE_SCOPE={re_scope}")


def test_format_results_with_high_success():
    """Test recommendation with high success probability (should be GO)."""
    results = {
        'probabilities': {
            'success': 90.0,
            'failure': 10.0,
        },
        'percentiles': {
            'duration': {'p10': 5.0, 'p50': 10.0, 'p90': 20.0},
            'cost': {'p10': 100.0, 'p50': 150.0, 'p90': 250.0},
        }
    }
    
    formatted = OutputFormatter.format_results(results)
    assert formatted.success_probability == 90.0, f"Expected success=90, got {formatted.success_probability}"
    assert formatted.risk_adjusted_recommendation == "GO", \
        f"Expected 'GO', got '{formatted.risk_adjusted_recommendation}'"
    
    print(f"✓ High success (90%) → {formatted.risk_adjusted_recommendation}")


def test_format_results_with_medium_success():
    """Test recommendation with medium success probability (should be CAUTION)."""
    results = {
        'probabilities': {
            'success': 60.0,
            'failure': 40.0,
        },
        'percentiles': {
            'duration': {'p10': 5.0, 'p50': 10.0, 'p90': 20.0},
            'cost': {'p10': 100.0, 'p50': 150.0, 'p90': 250.0},
        }
    }
    
    formatted = OutputFormatter.format_results(results)
    assert formatted.success_probability == 60.0, f"Expected success=60, got {formatted.success_probability}"
    assert formatted.risk_adjusted_recommendation == "CAUTION", \
        f"Expected 'CAUTION', got '{formatted.risk_adjusted_recommendation}'"
    
    print(f"✓ Medium success (60%) → {formatted.risk_adjusted_recommendation}")


def test_format_results_with_low_success():
    """Test recommendation with low success probability (should be NO-GO)."""
    results = {
        'probabilities': {
            'success': 30.0,
            'failure': 70.0,
        },
        'percentiles': {
            'duration': {'p10': 5.0, 'p50': 10.0, 'p90': 20.0},
            'cost': {'p10': 100.0, 'p50': 150.0, 'p90': 250.0},
        }
    }
    
    formatted = OutputFormatter.format_results(results)
    assert formatted.success_probability == 30.0, f"Expected success=30, got {formatted.success_probability}"
    assert formatted.risk_adjusted_recommendation == "NO-GO", \
        f"Expected 'NO-GO', got '{formatted.risk_adjusted_recommendation}'"
    
    print(f"✓ Low success (30%) → {formatted.risk_adjusted_recommendation}")


def test_format_results_with_explicit_thresholds():
    """Test format_results with explicitly provided thresholds."""
    results = {
        'probabilities': {
            'success': 70.0,
            'failure': 30.0,
        },
        'percentiles': {
            'duration': {'p10': 5.0, 'p50': 10.0, 'p90': 20.0},
            'cost': {'p10': 100.0, 'p50': 150.0, 'p90': 250.0},
        }
    }
    
    # With default thresholds: 70 should be CAUTION (50 <= 70 < 80)
    formatted = OutputFormatter.format_results(results)
    assert formatted.risk_adjusted_recommendation == "CAUTION"
    
    # With custom thresholds: 70 should be GO (if go_threshold=60)
    formatted = OutputFormatter.format_results(results, go_threshold=60.0)
    assert formatted.risk_adjusted_recommendation == "GO", \
        f"Expected 'GO' with custom threshold, got '{formatted.risk_adjusted_recommendation}'"
    
    print(f"✓ Explicit threshold override works")


def test_narrative_generation():
    """Test that narrative is generated correctly."""
    results = {
        'probabilities': {
            'success': 85.0,
            'failure': 15.0,
        },
        'percentiles': {
            'duration': {'p10': 5.0, 'p50': 10.0, 'p90': 20.0},
            'cost': {'p10': 100.0, 'p50': 150.0, 'p90': 250.0},
        }
    }
    
    formatted = OutputFormatter.format_results(results)
    narrative = formatted.summary_narrative
    
    assert "85" in str(narrative), "Success probability should be in narrative"
    assert "GO" in narrative, "Recommendation should be in narrative"
    assert "high probability" in narrative, "Summary should mention high probability"
    
    print(f"✓ Narrative generation works:\n   {narrative[:100]}...")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("BUG FIX #3: Type Mismatch in Recommendation Thresholds")
    print("="*60 + "\n")
    
    try:
        test_safe_extract_threshold_scalar()
        test_safe_extract_threshold_dict()
        test_safe_extract_threshold_fallback()
        test_load_thresholds_from_config()
        test_format_results_with_high_success()
        test_format_results_with_medium_success()
        test_format_results_with_low_success()
        test_format_results_with_explicit_thresholds()
        test_narrative_generation()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print("\nFix Summary:")
        print("  • Safe threshold extraction from config (scalar or dict)")
        print("  • Automatic conversion from decimal (0.0-1.0) to percentage (0-100)")
        print("  • Fallback to defaults if config has wrong structure")
        print("  • Correct recommendations: GO (>=80%), CAUTION (50-80%), NO-GO (<50%)")
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
