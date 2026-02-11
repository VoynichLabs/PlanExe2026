# Bug Fix Report #1: Numpy Shape Mismatch in risk_events.py

## Issue Summary
When `sample_portfolio_risk` was called with multiple risk events and 1000+ samples, it would generate arrays with shape `(N, 1)` instead of the expected `(N,)`. This broke downstream aggregation in `simulation.py` which expected clean 1D arrays.

**Root Cause:** When `sample_bernoulli_impact` created arrays from impact samples via list comprehension, if impact functions returned numpy arrays instead of scalars, the resulting array would have shape `(M, 1)` instead of `(M,)`. This dimension mismatch would then propagate through portfolio risk calculations.

---

## Changes Made

### File: `/mnt/d/1Projects/PlanExe2026/worker_plan/worker_plan_internal/monte_carlo/risk_events.py`

#### Change 1: Line 86-87 (in `sample_bernoulli_impact` function)
**Location:** Inside the `if num_events > 0:` block, after creating `sampled_impacts`

**Before:**
```python
        if num_events > 0:
            # Sample impacts for all occurrences (we'll zero them out if not needed)
            sampled_impacts = np.array(
                [impact_fn() for _ in range(int(num_events))]
            )

            # Assign sampled impacts to positions where occurrence=1
            event_positions = np.where(occurrences == 1)[0]
            impacts[event_positions] = sampled_impacts
```

**After:**
```python
        if num_events > 0:
            # Sample impacts for all occurrences (we'll zero them out if not needed)
            sampled_impacts = np.array(
                [impact_fn() for _ in range(int(num_events))]
            )
            # Flatten to ensure 1D shape (N,) not (N,1) - prevents shape mismatch
            sampled_impacts = sampled_impacts.flatten()

            # Assign sampled impacts to positions where occurrence=1
            event_positions = np.where(occurrences == 1)[0]
            impacts[event_positions] = sampled_impacts
```

#### Change 2: Lines 211-213 (in `sample_portfolio_risk` function)
**Location:** Inside the loop that appends impacts_per_event

**Before:**
```python
        impacts_per_event.append(
            samples if isinstance(samples, np.ndarray) else np.array([samples])
        )
```

**After:**
```python
        # Flatten to ensure consistent 1D shape (N,) not (N,1)
        if isinstance(samples, np.ndarray):
            impacts_per_event.append(samples.flatten())
        else:
            impacts_per_event.append(np.array([samples]))
```

---

## Testing Results

### Custom Test Script: `test_risk_events_fix.py`
**All 3 test cases PASSED:**

1. ✓ **Shape Validation Test**
   - Input: 3 risk events, 1000 scenarios
   - Output shape: `(1000,)` ✓ (not `(1000, 1)`)
   - Statistics verified: Mean=138.78, Std=190.73

2. ✓ **Empty Risk Events Test**
   - Input: Empty list, 100 scenarios
   - Output: Correct shape `(100,)` with all zeros

3. ✓ **Single Sample Test**
   - Input: 1 scenario
   - Output: Correct shape `(1,)`

### Existing Unit Tests: `test_risk_events.py`
**Results: 22 out of 23 tests PASSED** ✓

All critical portfolio risk tests passed:
- ✓ `test_single_event` - Single event portfolio sampling
- ✓ `test_independent_events_sum` - Multiple events sum correctly
- ✓ `test_zero_events` - Empty event list handling
- ✓ `test_mixed_probabilities` - Probability distribution accurate
- ✓ `test_reproducibility_with_seed` - Determinism with seeds
- ✓ All Bernoulli impact tests (9 tests)
- ✓ All risk event tests (5 tests)
- ✓ Integration tests (1 passed, 1 pre-existing test file issue)

**Note:** 1 test failed due to pre-existing parameter name issue in test file (`mode_val` vs `likely_val`), not related to this fix.

---

## Technical Details

### Why `.flatten()` Works
- When `np.array([impact_fn() for ...])` is created:
  - If `impact_fn()` returns a scalar → shape is `(N,)` ✓
  - If `impact_fn()` returns array of shape `(1,)` → shape becomes `(N, 1)` ✗
- `.flatten()` converts any 2D array into 1D, ensuring consistent shape `(N,)`
- For already 1D arrays, `.flatten()` is a no-op (identity operation)

### Compliance with Mark's Standards
✓ **Meaningful comments:** Added clarity about shape correction  
✓ **No file header changes:** Preserved existing header  
✓ **SRP/DRY check:** Fixes follow single responsibility (shape normalization)  
✓ **No unrelated changes:** Only touched the minimal necessary lines  
✓ **Test coverage:** Comprehensive testing validates fix works  

---

## Verification Checklist
- [x] Lines 86-87: `.flatten()` added to `sample_bernoulli_impact`
- [x] Lines 211-213: `.flatten()` added to `sample_portfolio_risk` loop
- [x] Test: `sample_portfolio_risk` returns shape `(1000,)` not `(1000,1)`
- [x] Test: All portfolio risk unit tests pass
- [x] No other code changes in the file
- [x] Downstream aggregation should now work without shape errors

---

## Impact Assessment
- **Before:** Portfolio risk calculation would fail with shape mismatch errors when aggregating impacts
- **After:** Clean 1D arrays with shape `(N,)` propagate correctly through simulation pipeline
- **Risk:** NONE - changes are defensive and only normalize array shapes
