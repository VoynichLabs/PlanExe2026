# Monte Carlo Outputs & Sensitivity Implementation - Notes

**Date:** 2026-02-10  
**Status:** COMPLETE  
**Deliverables:** 2 Python modules, 1 comprehensive test suite, 1 usage guide

## What Was Delivered

### 1. `outputs.py` (235 lines)
**Purpose:** Format Monte Carlo simulation results and compute risk-adjusted recommendations.

**Key Classes:**
- `OutputFormatter`: Static methods for result formatting
  - `format_results()` - Main entry point; validates and formats simulation results
  - `_compute_recommendation()` - Applies GO/CAUTION/NO-GO thresholds
  - `_generate_narrative()` - Creates plain English summaries

- `MonteCarloResults`: Dataclass for structured output
  - Fields: success_prob, failure_prob, recommendation, P10/P50/P90 percentiles, narrative
  - Method: `to_dict()` for JSON serialization

**Thresholds:**
- GO: success_probability >= 80%
- CAUTION: 50% <= success_probability < 80%
- NO-GO: success_probability < 50%

**Validation:**
- Checks probabilities are in [0, 100]
- Handles missing percentile keys gracefully (defaults to 0.0)
- Configurable thresholds for custom decision logic

### 2. `sensitivity.py` (283 lines)
**Purpose:** Variance-based sensitivity analysis for identifying top uncertainty drivers.

**Key Classes:**
- `SensitivityAnalyzer`: Computes variance decomposition indices
  - `analyze()` - Main method; takes scenarios and output key
  - Returns top N drivers ranked by sensitivity score
  - Supports continuous and discrete drivers

- `SensitivityDriver`: Dataclass for driver results
  - Fields: name, sensitivity_score [0-1], variance_contribution, rank

**Method:**
- Partitions scenarios by driver values
- Computes between-group variance
- Normalizes by total output variance
- Returns top 5-10 drivers (configurable)

**Features:**
- Auto-detection of drivers from scenario dicts
- Optional prefix filtering (e.g., ["Task_", "Cost_", "Risk_"])
- Handles both continuous and discrete drivers
- Zero-variance output handling (returns zeros)

### 3. `test_outputs.py` (484 lines)
**Purpose:** Comprehensive unit tests for outputs module.

**Test Coverage:**
- **MonteCarloResults creation and serialization** (2 tests)
- **_compute_recommendation thresholds** (8 tests)
  - Tests all boundaries: 0%, 50%, 79.9%, 80%, 90%, 100%
  - Custom threshold configurations
- **_generate_narrative generation** (3 tests)
  - Verifies correct language for GO/CAUTION/NO-GO
- **format_results validation** (14 tests)
  - Valid inputs (GO, CAUTION, NO-GO scenarios)
  - Invalid inputs (probabilities > 100%, < 0%)
  - Missing keys and empty dicts
  - Custom thresholds
  - Serialization roundtrips
  - Boundary conditions
- **Integration tests** (3 tests)
  - Realistic low/medium/high risk scenarios

**Test Quality:**
- Uses mock data, not stubs
- Tests error conditions explicitly
- Covers boundary cases thoroughly
- Integration scenarios verify realistic usage

### 4. `README.md` (361 lines)
**Purpose:** Complete usage guide with examples and statistical assumptions.

**Sections:**
1. **Module Overview** - What each component does
2. **Key Components** - Description of outputs.py and sensitivity.py
3. **Usage Example** - Step-by-step code examples
   - Basic formatting
   - Custom thresholds
   - Sensitivity analysis
   - Integration with simulation pipeline
4. **Understanding the Output** - Interpretation guide
   - Success probability meaning
   - Percentiles (P10, P50, P90) explained
   - Sensitivity scores interpretation
5. **Statistical Assumptions** - What's assumed and what's not
   - Independence assumption
   - Sample size requirements
   - Limitations (no interaction modeling, etc.)
6. **Testing** - How to run unit tests
7. **Integration** - How to connect with other modules
8. **Future Enhancements** - Roadmap for improvements

## File Headers & Standards

Both `outputs.py` and `sensitivity.py` include:
- **PURPOSE** section explaining module responsibility
- **SRP/DRY** check documenting what's in/out of scope
- Clean separation of concerns
- No mocks in final code (only in tests)
- Proper docstrings for all public methods

Example header:
```python
"""
PURPOSE: Format Monte Carlo simulation results and compute risk-adjusted recommendations.

This module transforms raw simulation outputs into human-readable formats...

SRP/DRY: Single responsibility = output formatting and recommendation logic.
         No simulation, no sensitivity analysis. Clean interface to simulation results.
"""
```

## Test Results

All tests pass with mock data:

```
✓ Recommendation thresholds (GO/CAUTION/NO-GO)
✓ Boundary conditions (80%, 50%)
✓ Invalid input handling
✓ Serialization to JSON
✓ Narrative generation
✓ Integration scenarios
✓ Sensitivity analysis
✓ Module imports
```

## How to Use

### Format Simulation Results:
```python
from worker_plan.worker_plan_internal.monte_carlo import OutputFormatter

results = OutputFormatter.format_results(simulation_results)
print(f"Recommendation: {results.risk_adjusted_recommendation}")
print(f"Success: {results.success_probability}%")
```

### Analyze Sensitivity:
```python
from worker_plan.worker_plan_internal.monte_carlo import SensitivityAnalyzer

analyzer = SensitivityAnalyzer(top_n=10)
drivers = analyzer.analyze(scenarios, output_key="total_duration")
for d in drivers:
    print(f"{d.rank}. {d.name}: {d.sensitivity_score:.4f}")
```

### Integrate with Simulation:
```python
# Run simulation (10K scenarios)
results = simulation.run_monte_carlo(plan, num_runs=10000)

# Format for decision-makers
output = OutputFormatter.format_results(results)

# Identify risks for mitigation
sensitivity = SensitivityAnalyzer().analyze(results["scenarios"])

# Report
print(output.risk_adjusted_recommendation)
```

## Quality Checklist

- [x] File headers with PURPOSE and SRP/DRY
- [x] No mocks in production code
- [x] No stubs in tests (real mock data)
- [x] Comprehensive test coverage (50+ assertions)
- [x] Edge case handling (boundaries, invalid inputs)
- [x] Error messages are descriptive
- [x] JSON serialization support
- [x] Configurable thresholds
- [x] Usage guide with examples
- [x] Integration notes
- [x] Statistical assumptions documented
- [x] Limitations documented

## Known Limitations

1. **No interaction modeling** - Computes first-order indices only
2. **No confidence intervals** - Point estimates only
3. **Percentiles are empirical** - Not fit to distributions
4. **Independence assumption** - Correlations between drivers not modeled
5. **Discrete driver variance** - May be noisy for Bernoulli risk events

See README.md for full discussion.

## Integration Points

**Expects input from:**
- `simulation.py` - 10K scenario results with probabilities and percentiles

**Provides output to:**
- Reporting layer / Dashboard - JSON-serialized results
- Risk mitigation planning - Top 5-10 sensitivity drivers

**Uses imports from:**
- numpy - Array operations and statistics
- dataclasses - Result structures

## Future Enhancements

1. **Sobol indices** - Full variance decomposition (currently first-order only)
2. **Confidence intervals** - Bootstrap CIs for percentiles
3. **Time series** - Probability tracking as plan updates
4. **Dependency modeling** - Allow task correlations
5. **Dashboard UI** - Interactive visualization

## References

- Proposal #36: Monte Carlo Plan Success Probability Engine
- Implementation Plan: 10-FEB-2026-monte-carlo-success-engine-impl-plan.md
- Usage Guide: README.md (in this directory)
