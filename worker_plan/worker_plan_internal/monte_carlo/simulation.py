"""
PURPOSE: Core Monte Carlo simulation engine for plan success probability estimation.

Runs 10,000 independent stochastic scenarios and computes success/failure probabilities,
percentile outcomes, and risk metrics.

SINGLE RESPONSIBILITY:
- Execute N independent scenarios for a given plan
- Sample task durations, costs, and risk events
- Aggregate results and compute statistics (success rate, percentiles)
- Return raw results dict (no I/O, no formatting)

CONSTRAINTS:
- No mocks or stubs; uses real numpy/scipy distributions
- Does NOT handle file I/O, database queries, or output formatting
- Does NOT modify input plan; reads only
"""

import numpy as np
from distributions import DurationSampler, CostSampler, RiskEventSampler
from config import NUM_RUNS, RANDOM_SEED, SUCCESS_DEADLINE_BUFFER_DAYS, SUCCESS_BUDGET_TOLERANCE, SUCCESS_CRITICAL_RISK_LIMIT, PERCENTILES


class MonteCarloSimulation:
    """
    Monte Carlo simulation engine for project plan success probability.
    
    Runs N scenarios (default 10,000) where each scenario:
    - Samples all task durations from uncertainty distributions
    - Samples all task costs from uncertainty distributions
    - Samples risk event occurrences and impacts
    - Aggregates results to compute total duration and cost
    - Determines success/failure based on thresholds
    """

    def __init__(self, num_runs=NUM_RUNS, random_seed=RANDOM_SEED):
        """
        Initialize simulation engine.
        
        Args:
            num_runs: Number of Monte Carlo scenarios to run (default 10,000)
            random_seed: Random seed for reproducibility (None = random)
        """
        self.num_runs = num_runs
        self.random_seed = random_seed
        
        if random_seed is not None:
            np.random.seed(random_seed)

    def run(self, plan):
        """
        Execute Monte Carlo simulation on a plan.
        
        Args:
            plan: Dict with structure:
                {
                    "name": str,
                    "deadline_days": float or None,
                    "budget": float or None,
                    "tasks": [
                        {
                            "id": str,
                            "name": str,
                            "duration_min": float,
                            "duration_likely": float,
                            "duration_max": float,
                            "cost_min": float,
                            "cost_likely": float,
                            "cost_max": float,
                        },
                        ...
                    ],
                    "risk_events": [
                        {
                            "id": str,
                            "name": str,
                            "probability": float,
                            "impact_duration": float,  # additional days
                            "impact_cost": float,  # additional cost
                        },
                        ...
                    ]
                }
            
        Returns:
            Dict with simulation results:
            {
                "num_runs": int,
                "success_count": int,
                "failure_count": int,
                "success_probability": float (0-1),
                "failure_probability": float (0-1),
                "delay_probability": float,
                "budget_overrun_probability": float,
                "durations": np.array (all 10k scenario durations),
                "costs": np.array (all 10k scenario costs),
                "duration_percentiles": {10: float, 50: float, 90: float},
                "cost_percentiles": {10: float, 50: float, 90: float},
                "recommendation": str ("GO", "RE-SCOPE", or "NO-GO"),
            }
        """
        # Validate input
        if not plan or "tasks" not in plan:
            raise ValueError("plan must contain 'tasks' list")
        
        if len(plan["tasks"]) == 0:
            raise ValueError("plan must have at least one task")
        
        # Pre-allocate result arrays
        durations = np.zeros(self.num_runs)
        costs = np.zeros(self.num_runs)
        success_flags = np.zeros(self.num_runs, dtype=bool)
        delay_flags = np.zeros(self.num_runs, dtype=bool)
        overrun_flags = np.zeros(self.num_runs, dtype=bool)
        
        # Run simulations
        for scenario_idx in range(self.num_runs):
            scenario_duration, scenario_cost, scenario_success, scenario_delay, scenario_overrun = \
                self._run_scenario(plan, scenario_idx)
            
            durations[scenario_idx] = scenario_duration
            costs[scenario_idx] = scenario_cost
            success_flags[scenario_idx] = scenario_success
            delay_flags[scenario_idx] = scenario_delay
            overrun_flags[scenario_idx] = scenario_overrun
        
        # Aggregate results
        success_count = int(np.sum(success_flags))
        failure_count = self.num_runs - success_count
        delay_count = int(np.sum(delay_flags))
        overrun_count = int(np.sum(overrun_flags))
        
        success_prob = success_count / self.num_runs
        failure_prob = failure_count / self.num_runs
        delay_prob = delay_count / self.num_runs
        overrun_prob = overrun_count / self.num_runs
        
        # Compute percentiles
        duration_percentiles = {p: float(np.percentile(durations, p)) for p in PERCENTILES}
        cost_percentiles = {p: float(np.percentile(costs, p)) for p in PERCENTILES}
        
        # Determine recommendation
        recommendation = self._get_recommendation(success_prob)
        
        return {
            "num_runs": self.num_runs,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_probability": round(success_prob, 3),
            "failure_probability": round(failure_prob, 3),
            "delay_probability": round(delay_prob, 3),
            "budget_overrun_probability": round(overrun_prob, 3),
            "durations": durations,
            "costs": costs,
            "duration_percentiles": {k: round(v, 1) for k, v in duration_percentiles.items()},
            "cost_percentiles": {k: round(v, 2) for k, v in cost_percentiles.items()},
            "recommendation": recommendation,
        }

    def _run_scenario(self, plan, scenario_idx):
        """
        Run a single Monte Carlo scenario.
        
        Args:
            plan: Plan dict
            scenario_idx: Scenario index (for logging/debugging)
            
        Returns:
            Tuple of (total_duration, total_cost, success_flag, delay_flag, overrun_flag)
        """
        total_duration = 0.0
        total_cost = 0.0
        
        # Sample task durations and costs
        for task in plan.get("tasks", []):
            duration = DurationSampler.sample_triangular(
                task.get("duration_min", 0),
                task.get("duration_likely", 0),
                task.get("duration_max", 0),
                size=1
            )[0]
            total_duration += duration
            
            cost = CostSampler.sample_pert_cost(
                task.get("cost_min", 0),
                task.get("cost_likely", 0),
                task.get("cost_max", 0),
                size=1
            )[0]
            total_cost += cost
        
        # Sample risk events
        critical_risks_triggered = 0
        for risk in plan.get("risk_events", []):
            occurred = RiskEventSampler.sample_bernoulli(
                risk.get("probability", 0.1),
                size=1
            )[0]
            
            if occurred:
                total_duration += risk.get("impact_duration", 0)
                total_cost += risk.get("impact_cost", 0)
                
                if risk.get("severity", "low") == "critical":
                    critical_risks_triggered += 1
        
        # Determine success/failure
        deadline = plan.get("deadline_days")
        budget = plan.get("budget")
        
        delay_flag = False
        overrun_flag = False
        
        if deadline is not None:
            delay_flag = total_duration > (deadline + SUCCESS_DEADLINE_BUFFER_DAYS)
        
        if budget is not None:
            overrun_flag = total_cost > (budget * SUCCESS_BUDGET_TOLERANCE)
        
        # Success = no delay AND no overrun AND no critical risks
        success = (not delay_flag) and (not overrun_flag) and (critical_risks_triggered <= SUCCESS_CRITICAL_RISK_LIMIT)
        
        return total_duration, total_cost, success, delay_flag, overrun_flag

    def _get_recommendation(self, success_probability):
        """
        Get go/no-go/re-scope recommendation based on success probability.
        
        Args:
            success_probability: Probability of success (0-1)
            
        Returns:
            String: "GO", "RE-SCOPE", or "NO-GO"
        """
        from config import GO_THRESHOLD, NO_GO_THRESHOLD, RE_SCOPE_THRESHOLD
        
        if success_probability >= GO_THRESHOLD:
            return "GO"
        elif success_probability < NO_GO_THRESHOLD:
            return "NO-GO"
        else:
            return "RE-SCOPE"
