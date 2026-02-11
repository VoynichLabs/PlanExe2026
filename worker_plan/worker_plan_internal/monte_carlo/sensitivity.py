"""
PURPOSE: Compute variance-based sensitivity analysis for Monte Carlo simulation outputs.

This module identifies the top uncertainty drivers (e.g., task durations, cost factors)
that contribute most to variance in project outcomes. Uses variance-based indices
(first-order Sobol-like approximation) without full Sobol algorithm complexity.

SRP/DRY: Single responsibility = sensitivity analysis only.
         No result formatting, no simulation, no recommendation logic.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import numpy as np


@dataclass
class SensitivityDriver:
    """Represents a single uncertainty driver and its sensitivity score.
    
    Attributes:
        name (str): Name of the driver (e.g., "Task_A_duration").
        sensitivity_score (float): Normalized sensitivity index [0, 1].
        variance_contribution (float): Contribution to total output variance.
        rank (int): Rank order (1 = most sensitive).
    """
    name: str
    sensitivity_score: float
    variance_contribution: float
    rank: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "sensitivity_score": round(self.sensitivity_score, 4),
            "variance_contribution": round(self.variance_contribution, 4),
            "rank": self.rank,
        }


class SensitivityAnalyzer:
    """
    Computes variance-based sensitivity indices for simulation drivers.
    
    Method: Variance decomposition approach.
    - For each potential driver (task duration, cost bucket, risk event),
      compute how much of output variance it explains.
    - Normalize by total variance to get first-order indices.
    - Return top N drivers sorted by sensitivity.
    
    Assumptions:
    - Drivers are approximately independent (no deep interactions modeled).
    - Output is scalar or aggregable to scalar (e.g., total duration, total cost).
    - Sufficient sample size (typically 1000+ scenarios for stability).
    """

    def __init__(self, top_n: int = 10):
        """
        Initialize analyzer.

        Args:
            top_n: Number of top drivers to return (default 10).
        """
        self.top_n = top_n

    def analyze(
        self,
        scenarios: List[Dict[str, Any]],
        output_key: str = "total_duration",
        driver_prefix_filters: List[str] = None,
    ) -> List[SensitivityDriver]:
        """
        Compute sensitivity indices for drivers in scenario list.

        Args:
            scenarios: List of scenario dicts, where each dict contains:
                - Keys for output (e.g., "total_duration", "total_cost")
                - Keys for individual drivers (e.g., "Task_A_duration", "Cost_Bucket_1")
                - Optionally risk event flags (e.g., "Risk_Event_Regulatory")
            output_key: Which output to compute sensitivity for (default "total_duration").
            driver_prefix_filters: If provided, only include drivers matching these
                                   prefixes (e.g., ["Task_", "Cost_", "Risk_"]).
                                   If None, auto-detect drivers.

        Returns:
            List of SensitivityDriver objects, sorted by sensitivity (descending).

        Raises:
            ValueError: If scenarios empty, output_key missing, or insufficient data.
        """
        if not scenarios:
            raise ValueError("scenarios list cannot be empty")

        # Extract output vector
        output_vector = np.array(
            [s.get(output_key, 0.0) for s in scenarios], dtype=float
        )
        if not np.any(np.isfinite(output_vector)):
            raise ValueError(f"output_key '{output_key}' has no finite values")

        # Identify available drivers
        drivers = self._identify_drivers(scenarios, driver_prefix_filters)
        if not drivers:
            raise ValueError("No drivers found in scenarios")

        # Compute sensitivity for each driver
        sensitivities = []
        total_variance = np.var(output_vector)

        # Avoid division by zero
        if total_variance < 1e-10:
            # Output has zero or near-zero variance, all drivers equally irrelevant
            return [
                SensitivityDriver(
                    name=d,
                    sensitivity_score=0.0,
                    variance_contribution=0.0,
                    rank=i + 1,
                )
                for i, d in enumerate(drivers[: self.top_n])
            ]

        for driver in drivers:
            score = self._compute_driver_variance_contribution(
                scenarios, output_vector, driver, total_variance
            )
            sensitivities.append((driver, score))

        # Sort by sensitivity descending
        sensitivities.sort(key=lambda x: x[1], reverse=True)

        # Build result list
        results = []
        for rank, (driver, variance_contrib) in enumerate(sensitivities[: self.top_n], 1):
            # Normalize to [0, 1] range
            normalized_score = min(1.0, max(0.0, variance_contrib / total_variance))
            results.append(
                SensitivityDriver(
                    name=driver,
                    sensitivity_score=normalized_score,
                    variance_contribution=variance_contrib,
                    rank=rank,
                )
            )

        return results

    @staticmethod
    def _identify_drivers(
        scenarios: List[Dict[str, Any]], filters: List[str] = None
    ) -> List[str]:
        """
        Identify all potential driver keys in scenario dicts.

        Args:
            scenarios: List of scenario dicts.
            filters: Optional list of prefixes to filter by
                    (e.g., ["Task_", "Cost_", "Risk_"]).

        Returns:
            Sorted list of unique driver names.
        """
        # Common outputs to exclude from drivers
        exclude_keywords = {
            "total_",
            "success",
            "failure",
            "outcome",
            "status",
            "metadata",
        }

        all_keys = set()
        for scenario in scenarios:
            for key in scenario.keys():
                # Skip known outputs and private keys
                if any(key.startswith(ex) for ex in exclude_keywords):
                    continue
                if key.startswith("_"):
                    continue
                all_keys.add(key)

        drivers = sorted(list(all_keys))

        # Apply filters if provided
        if filters:
            drivers = [d for d in drivers if any(d.startswith(f) for f in filters)]

        return drivers

    @staticmethod
    def _compute_driver_variance_contribution(
        scenarios: List[Dict[str, Any]],
        output_vector: np.ndarray,
        driver: str,
        total_variance: float,
    ) -> float:
        """
        Compute variance in output explained by a single driver.

        Uses a simple approach: partition scenarios by driver values,
        compute mean output per partition, and measure between-group variance.

        Args:
            scenarios: List of scenario dicts.
            output_vector: Output values as numpy array.
            driver: Driver name (key in scenario dicts).
            total_variance: Total variance of output (for normalization).

        Returns:
            Estimated variance contribution of this driver.
        """
        # Extract driver values
        driver_values = np.array(
            [s.get(driver, np.nan) for s in scenarios], dtype=float
        )

        # Skip if driver not present or all NaN
        if np.all(np.isnan(driver_values)):
            return 0.0

        # For continuous drivers, bin them to get meaningful groups
        # For discrete drivers, group by exact value
        unique_vals = len(np.unique(driver_values[~np.isnan(driver_values)]))

        if unique_vals > 20:
            # Likely continuous; bin into quantiles
            valid_mask = ~np.isnan(driver_values)
            bins = np.percentile(
                driver_values[valid_mask], [0, 25, 50, 75, 100]
            )
            # Avoid duplicate bin edges
            bins = np.unique(bins)
            if len(bins) < 2:
                bins = np.array([bins[0], bins[0] + 1])
            groups = np.digitize(driver_values, bins)
        else:
            # Discrete; use exact values as groups
            groups = np.where(np.isnan(driver_values), -1, driver_values).astype(int)

        # Compute mean output per group
        group_means = {}
        group_sizes = {}
        overall_mean = np.mean(output_vector)

        for group_id in np.unique(groups):
            if group_id == -1:  # NaN group
                continue
            mask = groups == group_id
            group_means[group_id] = np.mean(output_vector[mask])
            group_sizes[group_id] = np.sum(mask)

        # Between-group variance (explains how much of output varies by this driver)
        if not group_means:
            return 0.0

        between_variance = sum(
            group_sizes[gid] * (group_means[gid] - overall_mean) ** 2
            for gid in group_means
        ) / len(output_vector)

        return between_variance

    @staticmethod
    def to_dataframe_compatible(drivers: List[SensitivityDriver]) -> Dict[str, List]:
        """
        Convert sensitivity drivers to a format compatible with pandas/CSV.

        Args:
            drivers: List of SensitivityDriver objects.

        Returns:
            Dictionary with keys as column names, values as lists (one per row).
        """
        return {
            "rank": [d.rank for d in drivers],
            "driver": [d.name for d in drivers],
            "sensitivity_score": [round(d.sensitivity_score, 4) for d in drivers],
            "variance_contribution": [
                round(d.variance_contribution, 4) for d in drivers
            ],
        }
