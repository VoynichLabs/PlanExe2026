#!/usr/bin/env python3
"""
Test script to verify bug #1 fix: numpy shape mismatch in risk_events.py
Tests that sample_portfolio_risk returns clean 1D arrays, not (N,1) shaped arrays.
"""

import sys
import numpy as np

# Add path to the worker_plan module
sys.path.insert(0, '/mnt/d/1Projects/PlanExe2026')

from worker_plan.worker_plan_internal.monte_carlo.risk_events import (
    sample_portfolio_risk,
    sample_triangular,
)


def test_portfolio_risk_shape():
    """Test that sample_portfolio_risk returns 1D array of shape (N,)"""
    print("=" * 70)
    print("TEST: sample_portfolio_risk shape validation")
    print("=" * 70)
    
    # Define some test risk events
    risk_events = [
        {
            'probability': 0.3,
            'impact_fn': lambda: sample_triangular(100, 150, 200)
        },
        {
            'probability': 0.5,
            'impact_fn': lambda: sample_triangular(50, 75, 150)
        },
        {
            'probability': 0.2,
            'impact_fn': lambda: sample_triangular(200, 250, 300)
        },
    ]
    
    # Test with 1000 samples
    num_samples = 1000
    result = sample_portfolio_risk(risk_events, size=num_samples, random_state=42)
    
    print(f"\nInput: 3 risk events, {num_samples} scenarios")
    print(f"Result type: {type(result)}")
    print(f"Result shape: {result.shape}")
    print(f"Expected shape: ({num_samples},)")
    
    # Verify shape is 1D and correct size
    assert isinstance(result, np.ndarray), f"Expected ndarray, got {type(result)}"
    assert result.ndim == 1, f"Expected 1D array, got {result.ndim}D"
    assert result.shape == (num_samples,), f"Expected shape ({num_samples},), got {result.shape}"
    
    print(f"\n✓ Shape test PASSED")
    print(f"  - Result is 1D array: {result.ndim == 1}")
    print(f"  - Correct shape ({num_samples},): {result.shape == (num_samples,)}")
    print(f"  - NOT shape (N,1): {result.shape != (num_samples, 1)}")
    
    # Show some basic statistics
    print(f"\nStatistics of portfolio risk impacts:")
    print(f"  Mean: {np.mean(result):.2f}")
    print(f"  Std:  {np.std(result):.2f}")
    print(f"  Min:  {np.min(result):.2f}")
    print(f"  Max:  {np.max(result):.2f}")
    print(f"  Median: {np.median(result):.2f}")
    
    # Show first few values
    print(f"\nFirst 10 values: {result[:10]}")
    
    return True


def test_empty_events():
    """Test edge case: empty risk events list"""
    print("\n" + "=" * 70)
    print("TEST: Empty risk events list")
    print("=" * 70)
    
    result = sample_portfolio_risk([], size=100)
    
    print(f"Result shape: {result.shape}")
    print(f"Expected shape: (100,)")
    
    assert result.shape == (100,), f"Expected shape (100,), got {result.shape}"
    assert np.all(result == 0), "Expected all zeros for empty events"
    
    print("✓ Empty events test PASSED")
    return True


def test_single_sample():
    """Test edge case: single sample"""
    print("\n" + "=" * 70)
    print("TEST: Single sample")
    print("=" * 70)
    
    risk_events = [
        {
            'probability': 0.5,
            'impact_fn': lambda: sample_triangular(10, 15, 20)
        },
    ]
    
    result = sample_portfolio_risk(risk_events, size=1)
    
    print(f"Result: {result}")
    print(f"Result shape: {result.shape}")
    print(f"Result dtype: {result.dtype}")
    
    # Should be 1D array with 1 element
    assert isinstance(result, np.ndarray), f"Expected ndarray, got {type(result)}"
    assert result.ndim == 1, f"Expected 1D array, got {result.ndim}D"
    assert result.shape == (1,), f"Expected shape (1,), got {result.shape}"
    
    print("✓ Single sample test PASSED")
    return True


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("TESTING BUG FIX #1: Numpy shape mismatch in risk_events.py")
    print("=" * 70)
    
    all_passed = True
    try:
        test_portfolio_risk_shape()
        test_empty_events()
        test_single_sample()
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        all_passed = False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - Bug fix verified!")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)
    
    sys.exit(0 if all_passed else 1)
