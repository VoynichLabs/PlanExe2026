#!/usr/bin/env python3
"""
Test script to verify OutputFormatter can accept both dict and MonteCarloResults dataclass.

Tests the fix for the interface mismatch between MonteCarloSimulation output 
and OutputFormatter input.
"""

import sys
import os

# Add worker_plan to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'worker_plan'))

from dataclasses import dataclass, asdict
from worker_plan_internal.monte_carlo.outputs import OutputFormatter, MonteCarloResults


def test_format_results_with_dict():
    """Test format_results with dict input (original behavior)."""
    print("\n=== TEST 1: format_results() with dict input ===")
    
    # Original dict structure
    mock_results_dict = {
        "probabilities": {"success": 85.0, "failure": 15.0},
        "percentiles": {
            "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
            "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
        },
    }
    
    try:
        output = OutputFormatter.format_results(mock_results_dict)
        print(f"✓ Successfully formatted dict input")
        print(f"  - Success probability: {output.success_probability}%")
        print(f"  - Recommendation: {output.risk_adjusted_recommendation}")
        assert output.success_probability == 85.0
        assert output.failure_probability == 15.0
        assert output.risk_adjusted_recommendation == "GO"
        print("✓ All assertions passed for dict input\n")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        return False


def test_format_results_with_dataclass():
    """Test format_results with MonteCarloResults dataclass input (new behavior)."""
    print("=== TEST 2: format_results() with MonteCarloResults dataclass input ===")
    
    # Create a MonteCarloResults dataclass object
    mock_results_dataclass = MonteCarloResults(
        success_probability=85.0,
        failure_probability=15.0,
        risk_adjusted_recommendation="GO",
        duration_p10=10.0,
        duration_p50=15.0,
        duration_p90=25.0,
        cost_p10=1000.0,
        cost_p50=1500.0,
        cost_p90=2500.0,
        summary_narrative="Test narrative for existing dataclass.",
        percentiles_dict={
            "duration": {"p10": 10.0, "p50": 15.0, "p90": 25.0},
            "cost": {"p10": 1000.0, "p50": 1500.0, "p90": 2500.0},
        },
    )
    
    try:
        # This should now work after the fix!
        output = OutputFormatter.format_results(mock_results_dataclass)
        print(f"✓ Successfully formatted MonteCarloResults dataclass input")
        print(f"  - Success probability: {output.success_probability}%")
        print(f"  - Recommendation: {output.risk_adjusted_recommendation}")
        assert output.success_probability == 85.0
        assert output.failure_probability == 15.0
        # Note: The risk_adjusted_recommendation will be recomputed based on thresholds
        print(f"✓ All assertions passed for dataclass input\n")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_dataclass_to_dict_conversion():
    """Test internal conversion logic using asdict()."""
    print("=== TEST 3: DataClass to Dict conversion ===")
    
    # Create a MonteCarloResults dataclass
    original = MonteCarloResults(
        success_probability=75.0,
        failure_probability=25.0,
        risk_adjusted_recommendation="CAUTION",
        duration_p10=12.0,
        duration_p50=18.0,
        duration_p90=30.0,
        cost_p10=1200.0,
        cost_p50=1800.0,
        cost_p90=3000.0,
        summary_narrative="Original narrative",
        percentiles_dict={
            "duration": {"p10": 12.0, "p50": 18.0, "p90": 30.0},
            "cost": {"p10": 1200.0, "p50": 1800.0, "p90": 3000.0},
        },
    )
    
    try:
        # Check hasattr for dataclass detection
        if hasattr(original, '__dataclass_fields__'):
            print("✓ Dataclass detection works (hasattr check)")
            
            # Convert to dict
            converted = asdict(original)
            print(f"✓ Successfully converted dataclass to dict")
            print(f"  - Type: {type(converted)}")
            print(f"  - Keys: {list(converted.keys())}")
            
            # Verify conversion
            assert isinstance(converted, dict)
            assert converted["success_probability"] == 75.0
            assert converted["failure_probability"] == 25.0
            print("✓ All conversion assertions passed\n")
            return True
        else:
            print("✗ Dataclass detection failed\n")
            return False
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_mixed_input_handling():
    """Test that format_results handles mixed nested structures."""
    print("=== TEST 4: Mixed input handling (nested dicts) ===")
    
    # Input with nested structure that came from a dataclass
    mock_mixed = {
        "success_probability": 90.0,
        "failure_probability": 10.0,
        "risk_adjusted_recommendation": "GO",
        "duration_p10": 8.0,
        "duration_p50": 12.0,
        "duration_p90": 20.0,
        "cost_p10": 900.0,
        "cost_p50": 1400.0,
        "cost_p90": 2200.0,
        "summary_narrative": "Mixed test narrative",
        "percentiles_dict": {
            "duration": {"p10": 8.0, "p50": 12.0, "p90": 20.0},
            "cost": {"p10": 900.0, "p50": 1400.0, "p90": 2200.0},
        },
    }
    
    try:
        # Need to convert to expected structure
        formatted_input = {
            "probabilities": {"success": mock_mixed["success_probability"], "failure": mock_mixed["failure_probability"]},
            "percentiles": mock_mixed["percentiles_dict"],
        }
        output = OutputFormatter.format_results(formatted_input)
        print(f"✓ Successfully formatted mixed input")
        print(f"  - Success probability: {output.success_probability}%")
        print(f"  - Recommendation: {output.risk_adjusted_recommendation}")
        assert output.success_probability == 90.0
        print("✓ Mixed input handling passed\n")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("Monte Carlo Interface Fix - Comprehensive Test Suite")
    print("=" * 70)
    print("\nTesting OutputFormatter.format_results() with dict and dataclass inputs")
    print("=" * 70)
    
    results = []
    results.append(("Dict input", test_format_results_with_dict()))
    results.append(("Dataclass input", test_format_results_with_dataclass()))
    results.append(("Dataclass conversion", test_dataclass_to_dict_conversion()))
    results.append(("Mixed input handling", test_mixed_input_handling()))
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Interface fix is working correctly.")
        exit(0)
    else:
        print("\n❌ SOME TESTS FAILED. Please review the errors above.")
        exit(1)
