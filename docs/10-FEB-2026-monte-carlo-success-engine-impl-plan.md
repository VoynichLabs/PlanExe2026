# Implementation Plan: Monte Carlo Plan Success Probability Engine

**Author:** Larry  
**Date:** 10 FEB 2026  
**Goal:** Implement proposal #36 (Monte Carlo Plan Success Probability Engine) in Python  
**Target Repo:** PlanExe2026  
**Status:** PLANNING

---

## Scope

**In:**
- Core Monte Carlo simulation engine (numpy/scipy)
- Task duration uncertainty modeling (triangular, lognormal)
- Cost uncertainty modeling (PERT, lognormal)
- Risk event Bernoulli sampling
- Success/failure probability calculation
- P10/P50/P90 percentile outputs
- Tornado chart (sensitivity analysis) output
- Risk-adjusted recommendation logic
- Unit tests covering simulation accuracy

**Out:**
- Frontend dashboard integration (separate feature)
- Database schema changes (assume plan structure exists)
- Historical calibration against real project data (future work)

---

## Architecture

### Module Structure
```
worker_plan/worker_plan_internal/monte_carlo/
├── __init__.py
├── README.md
├── simulation.py           # Core Monte Carlo engine
├── distributions.py        # Uncertainty models (triangular, PERT, lognormal)
├── risk_events.py         # Risk event sampling
├── outputs.py             # Result aggregation & formatting
├── sensitivity.py         # Tornado chart (Sobol indices)
├── config.py              # Simulation parameters
└── tests/
    ├── test_distributions.py
    ├── test_simulation.py
    ├── test_outputs.py
    └── test_end_to_end.py
```

### Key Responsibilities
- **simulation.py:** Run 10,000 scenarios, aggregate results, compute probabilities
- **distributions.py:** Task duration and cost sampling with proper statistical models
- **risk_events.py:** Bernoulli risk sampling with impact distributions
- **outputs.py:** Format results (success %, P10/P50/P90, go/no-go recommendation)
- **sensitivity.py:** Identify top uncertainty drivers

### Dependencies
- numpy (array operations, statistical functions)
- scipy (triangular, lognormal distributions, statistics)
- pandas (optional, for result formatting)
- Existing PlanExe plan data structures (reuse without modification)

---

## TODOs (Ordered)

### Phase 1: Core Simulation (Sub-agent #1)
- [ ] Create module structure and __init__.py
- [ ] Write distributions.py with triangular, PERT, lognormal samplers
- [ ] Write risk_events.py with Bernoulli + impact sampling
- [ ] Unit tests for both modules

### Phase 2: Simulation Engine (Sub-agent #2)
- [ ] Write simulation.py: main 10K-run loop, aggregation logic
- [ ] Implement success/failure probability calculation
- [ ] Calculate P10/P50/P90 percentiles
- [ ] Unit tests for simulation accuracy

### Phase 3: Outputs & Sensitivity (Sub-agent #3)
- [ ] Write outputs.py: format results, risk-adjusted recommendations
- [ ] Write sensitivity.py: Tornado chart (Sobol first-order indices)
- [ ] Unit tests for output formatting and sensitivity

### Phase 4: Integration & Verification (Main session)
- [ ] Create simple integration test with mock plan data
- [ ] Verify results are reasonable (e.g., P50 close to mean)
- [ ] Add README with usage examples
- [ ] Code review with Mark (before PR)

---

## Implementation Notes

### Simulation Model
- Each task has min, likely, max duration → sample triangular
- Each cost bucket has estimate + std dev → sample lognormal (σ = estimate * variance factor)
- Risk events: Define probability + impact distribution
- Run 10,000 independent scenarios
- Track: task durations, costs, whether risk events triggered, final success/failure

### Success/Failure Logic
- Success = on-time AND on-budget AND no critical failures
- Failure = missed deadline OR cost overrun OR critical risk triggered
- Output: P(success), P(failure), P(overrun), P(delay)

### Sensitivity Analysis (Tornado Chart)
- Compute Sobol first-order indices for top 5-10 drivers
- Identify which tasks/costs cause most variance in outcome
- Output: list of (driver_name, sensitivity_score)

---

## Testing Strategy

- **Unit tests:** Each module tested independently with mock data
- **Integration test:** Mock plan with 5 tasks, run simulation, verify statistics make sense
- **Accuracy check:** P50 should be ~mean of distribution, P90 > P50, etc.

---

## Definition of Done

- [ ] All tests pass
- [ ] Code follows Mark's standards (file headers, SRP/DRY, no mocks in final code)
- [ ] README explains usage with worked example
- [ ] Results are reasonable and match statistical expectations
- [ ] PR opened with meaningful commit message

---

## Potential Blockers

1. Plan data structure unknown → will infer from existing PlanExe code
2. Risk event specification format unknown → will create reasonable defaults

---

## Next Step

Spawn 3 sub-agents:
1. Distributions & risk events modules
2. Simulation engine
3. Outputs & sensitivity analysis

Then integrate in main session.
