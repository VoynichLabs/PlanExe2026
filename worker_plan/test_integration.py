"""Integration test for Monte Carlo modules."""
import sys
import numpy as np

# Test imports
print("=" * 60)
print("TESTING MODULE IMPORTS")
print("=" * 60)

try:
    from worker_plan_internal.monte_carlo.distributions import (
        sample_triangular,
        sample_pert,
        sample_lognormal,
    )
    print("✓ Basic distribution functions imported successfully")
except ImportError as e:
    print(f"✗ Failed to import distributions: {e}")
    sys.exit(1)

# Check if compute_lognormal_params exists
try:
    from worker_plan_internal.monte_carlo.distributions import compute_lognormal_params
    print("✓ compute_lognormal_params imported")
    has_compute = True
except ImportError:
    print("✗ compute_lognormal_params NOT found (missing implementation)")
    has_compute = False

# Test basic distribution sampling
print("\n" + "=" * 60)
print("TESTING BASIC DISTRIBUTIONS")
print("=" * 60)

try:
    tri_sample = sample_triangular(min_val=1.0, likely_val=2.0, max_val=3.0, size=10)
    print(f"✓ Triangular sample: shape={tri_sample.shape}, range=[{tri_sample.min():.2f}, {tri_sample.max():.2f}]")
    assert tri_sample.min() >= 1.0 and tri_sample.max() <= 3.0, "Triangular out of bounds"
except Exception as e:
    print(f"✗ Triangular sampling failed: {e}")

try:
    pert_sample = sample_pert(min_val=1.0, likely_val=2.0, max_val=3.0, size=10)
    print(f"✓ PERT sample: shape={pert_sample.shape}, range=[{pert_sample.min():.2f}, {pert_sample.max():.2f}]")
except Exception as e:
    print(f"✗ PERT sampling failed: {e}")

try:
    lognorm_sample = sample_lognormal(mu=0.0, sigma=0.5, size=10)
    print(f"✓ Lognormal sample: shape={lognorm_sample.shape}, range=[{lognorm_sample.min():.2f}, {lognorm_sample.max():.2f}]")
except Exception as e:
    print(f"✗ Lognormal sampling failed: {e}")

# Test risk_events
print("\n" + "=" * 60)
print("TESTING RISK EVENTS")
print("=" * 60)

try:
    from worker_plan_internal.monte_carlo.risk_events import (
        sample_bernoulli_impact,
        sample_risk_event,
        sample_portfolio_risk,
    )
    print("✓ Risk event functions imported")
except ImportError as e:
    print(f"✗ Failed to import risk_events: {e}")
    sys.exit(1)

# Test simple Bernoulli impact
try:
    def impact_fn():
        return 100.0
    
    result = sample_bernoulli_impact(probability=0.5, impact_fn=impact_fn, size=10)
    print(f"✓ Bernoulli impact: shape={result.shape}, dtype={result.dtype}, sum={result.sum():.2f}")
    assert result.shape == (10,), f"Expected shape (10,), got {result.shape}"
except Exception as e:
    print(f"✗ Bernoulli impact failed: {e}")

# Test risk event with triangular impact
try:
    result = sample_risk_event(
        probability=0.5,
        impact_min=10.0,
        impact_max=100.0,
        impact_mode=50.0,
        impact_distribution="triangular",
        size=10,
        random_state=42
    )
    print(f"✓ Risk event (triangular): shape={result.shape}, range=[{result.min():.2f}, {result.max():.2f}]")
    assert result.shape == (10,), f"Expected shape (10,), got {result.shape}"
except Exception as e:
    print(f"✗ Risk event (triangular) failed: {e}")

# Test simulation  
print("\n" + "=" * 60)
print("TESTING SIMULATION")
print("=" * 60)

try:
    from worker_plan_internal.monte_carlo.simulation import MonteCarloSimulation
    print("✓ MonteCarloSimulation imported")
except ImportError as e:
    print(f"✗ Failed to import simulation: {e}")

# Test outputs
print("\n" + "=" * 60)
print("TESTING OUTPUTS")
print("=" * 60)

try:
    from worker_plan_internal.monte_carlo.outputs import OutputFormatter
    print("✓ OutputFormatter imported")
except ImportError as e:
    print(f"✗ Failed to import outputs: {e}")

# Test sensitivity
print("\n" + "=" * 60)
print("TESTING SENSITIVITY")
print("=" * 60)

try:
    from worker_plan_internal.monte_carlo.sensitivity import SensitivityAnalyzer
    print("✓ SensitivityAnalyzer imported")
except ImportError as e:
    print(f"✗ Failed to import sensitivity: {e}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Critical missing: compute_lognormal_params = {not has_compute}")
