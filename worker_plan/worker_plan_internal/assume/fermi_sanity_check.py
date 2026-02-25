"""
Author: Larry (Claude Opus 4.6)
Date: 2026-02-25
PURPOSE: FermiSanityCheck validation task for QuantifiedAssumption objects.
Validates quantitative assumptions against bounds, span ratios, confidence/evidence requirements,
and domain-specific heuristics. Outputs validation_report.json with pass/fail status per assumption.
SRP/DRY check: Pass - Reuses QuantifiedAssumption schema + ConfidenceLevel enum from Egon's extractor.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from worker_plan_internal.assume.quantified_assumptions import (
    QuantifiedAssumption,
    ConfidenceLevel,
    QuantifiedAssumptionExtractor,
)

LOGGER = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Validation outcome."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"  # For non-quantifiable assumptions


@dataclass
class ValidationResult:
    """Result of validating a single assumption."""
    assumption_id: str
    status: ValidationStatus
    reasons: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)  # Non-blocking warnings

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    """Summary report from FermiSanityCheck run."""
    total_assumptions: int
    passed: int
    failed: int
    warnings: int
    skipped: int
    results: List[ValidationResult] = field(default_factory=list)
    heuristic_bounds_applied: Dict[str, Dict[str, float]] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Percentage of assumptions that passed validation."""
        valid_count = self.passed + self.failed + self.warnings
        if valid_count == 0:
            return 0.0
        return (self.passed / valid_count) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_assumptions": self.total_assumptions,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "skipped": self.skipped,
            "pass_rate_pct": round(self.pass_rate, 1),
            "heuristic_bounds": self.heuristic_bounds_applied,
            "results": [r.to_dict() for r in self.results],
        }


class FermiSanityCheck:
    """
    Validates QuantifiedAssumption objects against:
    1. Bounds completeness (lower + upper must be present for quantifiable claims)
    2. Span ratio (upper / lower should be ≤ 100× for most domains)
    3. Confidence + evidence alignment (low confidence requires detailed evidence)
    4. Domain heuristics (budget, timeline, team size ranges)
    """

    # Domain heuristic bounds (in base units)
    HEURISTIC_BOUNDS = {
        "budget": {"lower": 1_000, "upper": 100_000_000, "unit": "usd"},  # $1k - $100M
        "timeline": {"lower": 1, "upper": 3650, "unit": "days"},  # 1 day - 10 years
        "team": {"lower": 1, "upper": 1000, "unit": "people"},  # 1 - 1000 people
    }

    # Unit normalization (map common units to domain)
    UNIT_TO_DOMAIN = {
        # Budget
        "usd": "budget",
        "eur": "budget",
        "million": "budget",
        "billion": "budget",
        "k": "budget",
        # Timeline
        "days": "timeline",
        "weeks": "timeline",
        "months": "timeline",
        "years": "timeline",
        # Team
        "people": "team",
        "person": "team",
        "engineers": "team",
        "developers": "team",
        "team": "team",
    }

    # Span ratio threshold (upper / lower)
    MAX_SPAN_RATIO = 100.0
    WARN_SPAN_RATIO = 50.0  # Flag for warning even if passing

    def __init__(self):
        self.extractor = QuantifiedAssumptionExtractor()

    def validate(self, assumptions: List[QuantifiedAssumption]) -> ValidationReport:
        """
        Validate a list of QuantifiedAssumption objects.
        Returns ValidationReport with detailed results.
        """
        report = ValidationReport(
            total_assumptions=len(assumptions),
            heuristic_bounds_applied=self.HEURISTIC_BOUNDS,
        )

        for assumption in assumptions:
            result = self._validate_single(assumption)
            report.results.append(result)

            # Update summary counts
            if result.status == ValidationStatus.PASSED:
                report.passed += 1
            elif result.status == ValidationStatus.FAILED:
                report.failed += 1
            elif result.status == ValidationStatus.WARNING:
                report.warnings += 1
            elif result.status == ValidationStatus.SKIPPED:
                report.skipped += 1

        LOGGER.info(
            "FermiSanityCheck complete: %d passed, %d failed, %d warnings, %d skipped",
            report.passed,
            report.failed,
            report.warnings,
            report.skipped,
        )
        return report

    def _validate_single(self, assumption: QuantifiedAssumption) -> ValidationResult:
        """Validate a single assumption against all checks."""
        result = ValidationResult(assumption_id=assumption.assumption_id)

        # Check 1: Bounds completeness
        if assumption.lower_bound is None or assumption.upper_bound is None:
            # Non-quantifiable assumptions are skipped, not failed
            if not assumption.extracted_numbers:
                result.status = ValidationStatus.SKIPPED
                result.reasons.append("No numeric bounds detected; assumption is qualitative")
                return result

        # Check 2: Span ratio
        if assumption.span_ratio is not None:
            if assumption.span_ratio > self.MAX_SPAN_RATIO:
                result.status = ValidationStatus.FAILED
                result.reasons.append(
                    f"Span ratio {assumption.span_ratio:.1f}× exceeds threshold {self.MAX_SPAN_RATIO}× "
                    f"({assumption.lower_bound} to {assumption.upper_bound}). "
                    "Range is too wide; split into tighter estimates or provide additional constraints."
                )
            elif assumption.span_ratio > self.WARN_SPAN_RATIO:
                result.flags.append(
                    f"Span ratio {assumption.span_ratio:.1f}× is wide (approaching {self.MAX_SPAN_RATIO}×). "
                    "Consider tightening bounds."
                )

        # Check 3: Confidence + evidence alignment
        if assumption.confidence == ConfidenceLevel.low:
            if not assumption.evidence or len(assumption.evidence.strip()) < 10:
                result.status = ValidationStatus.FAILED
                result.reasons.append(
                    f"Low confidence claim '{assumption.claim}' lacks sufficient evidence. "
                    "Provide source, reference, or reasoning."
                )
        elif assumption.confidence == ConfidenceLevel.medium:
            if not assumption.evidence:
                result.flags.append("Medium confidence claim has no evidence; consider adding source.")

        # Check 4: Heuristic bounds (if unit maps to a domain)
        domain = self._infer_domain(assumption)
        if domain and domain in self.HEURISTIC_BOUNDS:
            heuristic = self.HEURISTIC_BOUNDS[domain]
            lower = heuristic["lower"]
            upper = heuristic["upper"]

            if assumption.lower_bound is not None and assumption.lower_bound < lower:
                result.flags.append(
                    f"Lower bound {assumption.lower_bound} {assumption.unit} is below typical {domain} range "
                    f"(typical: {lower}-{upper} {heuristic['unit']}). May indicate missing context."
                )
            if assumption.upper_bound is not None and assumption.upper_bound > upper:
                result.flags.append(
                    f"Upper bound {assumption.upper_bound} {assumption.unit} exceeds typical {domain} range "
                    f"(typical: {lower}-{upper} {heuristic['unit']}). Verify scope and constraints."
                )

        # Finalize status if not already set to failed
        if result.status == ValidationStatus.FAILED:
            pass  # Keep failed status
        elif result.flags:
            result.status = ValidationStatus.WARNING
        else:
            result.status = ValidationStatus.PASSED

        return result

    def _infer_domain(self, assumption: QuantifiedAssumption) -> Optional[str]:
        """Infer domain (budget, timeline, team) from unit or claim text."""
        if assumption.unit:
            unit_lower = assumption.unit.lower()
            if unit_lower in self.UNIT_TO_DOMAIN:
                return self.UNIT_TO_DOMAIN[unit_lower]

        # Fallback: check claim text for domain keywords
        claim_lower = assumption.claim.lower()
        if any(word in claim_lower for word in ["budget", "cost", "invest", "expense", "fee", "price"]):
            return "budget"
        if any(word in claim_lower for word in ["timeline", "schedule", "duration", "time", "month", "week", "day"]):
            return "timeline"
        if any(word in claim_lower for word in ["team", "staff", "people", "engineer", "developer", "resource"]):
            return "team"

        return None


class FermiSanityCheckTask:
    """
    Luigi-style task wrapper for FermiSanityCheck.
    Consumes MakeAssumptions output, extracts QuantifiedAssumptions, validates, outputs report.
    """

    def __init__(self, extractor: Optional[QuantifiedAssumptionExtractor] = None):
        self.extractor = extractor or QuantifiedAssumptionExtractor()
        self.fermi = FermiSanityCheck()

    def run(self, assumptions_list: List[Dict[str, Any]]) -> ValidationReport:
        """
        Run FermiSanityCheck on a list of raw assumption dicts.
        Returns ValidationReport.
        """
        # Extract structured assumptions
        quantified = self.extractor.extract(assumptions_list)
        LOGGER.info(f"Extracted {len(quantified)} quantified assumptions from input")

        # Validate
        report = self.fermi.validate(quantified)
        return report

    def output_report(self, report: ValidationReport, filepath: str) -> None:
        """Write ValidationReport to JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        LOGGER.info(f"Validation report written to {filepath}")
