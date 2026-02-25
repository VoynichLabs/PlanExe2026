"""
Unit tests for FermiSanityCheck validator.
Tests bounds validation, span ratios, confidence+evidence, and heuristic bounds.
"""

from worker_plan_internal.assume.quantified_assumptions import (
    QuantifiedAssumption,
    ConfidenceLevel,
)
from worker_plan_internal.assume.fermi_sanity_check import (
    FermiSanityCheck,
    ValidationStatus,
)


def test_valid_assumption_high_confidence():
    """High confidence with tight bounds should pass."""
    fermi = FermiSanityCheck()
    assumption = QuantifiedAssumption(
        assumption_id="test-1",
        question="What is the project budget?",
        claim="Budget is 5 to 7 million USD.",
        lower_bound=5_000_000,
        upper_bound=7_000_000,
        unit="usd",
        confidence=ConfidenceLevel.high,
        evidence="Approved budget from finance team.",
        extracted_numbers=[5_000_000, 7_000_000],
        raw_assumption="Assumption: Budget is 5 to 7 million USD.",
    )
    result = fermi._validate_single(assumption)
    assert result.status == ValidationStatus.PASSED
    assert len(result.reasons) == 0


def test_wide_span_ratio_fails():
    """Span ratio > 100× should fail."""
    fermi = FermiSanityCheck()
    assumption = QuantifiedAssumption(
        assumption_id="test-2",
        question="Estimate project cost?",
        claim="Could cost anywhere from 100k to 50 million.",
        lower_bound=100_000,
        upper_bound=50_000_000,
        unit="usd",
        confidence=ConfidenceLevel.low,
        evidence="Wild guess based on comparable projects.",
        extracted_numbers=[100_000, 50_000_000],
        raw_assumption="Assumption: Could cost anywhere from 100k to 50 million.",
    )
    result = fermi._validate_single(assumption)
    assert result.status == ValidationStatus.FAILED
    assert any("Span ratio" in reason for reason in result.reasons)


def test_low_confidence_without_evidence_fails():
    """Low confidence without sufficient evidence should fail."""
    fermi = FermiSanityCheck()
    assumption = QuantifiedAssumption(
        assumption_id="test-3",
        question="Timeline estimate?",
        claim="Estimate 6 to 12 months.",
        lower_bound=6,
        upper_bound=12,
        unit="months",
        confidence=ConfidenceLevel.low,
        evidence="",  # No evidence
        extracted_numbers=[6, 12],
        raw_assumption="Assumption: Estimate 6 to 12 months.",
    )
    result = fermi._validate_single(assumption)
    assert result.status == ValidationStatus.FAILED
    assert any("Low confidence" in reason for reason in result.reasons)


def test_qualitative_assumption_skipped():
    """Non-numeric assumptions should be skipped."""
    fermi = FermiSanityCheck()
    assumption = QuantifiedAssumption(
        assumption_id="test-4",
        question="Will the team commit?",
        claim="Team will be fully committed to the project.",
        lower_bound=None,
        upper_bound=None,
        unit=None,
        confidence=ConfidenceLevel.high,
        evidence="CEO verbal commitment.",
        extracted_numbers=[],
        raw_assumption="Assumption: Team will be fully committed to the project.",
    )
    result = fermi._validate_single(assumption)
    assert result.status == ValidationStatus.SKIPPED


def test_heuristic_bounds_budget_below_min():
    """Budget below $1k heuristic should warn."""
    fermi = FermiSanityCheck()
    assumption = QuantifiedAssumption(
        assumption_id="test-5",
        question="Hosting budget?",
        claim="Budget 50 to 100 USD per month.",
        lower_bound=50,
        upper_bound=100,
        unit="usd",
        confidence=ConfidenceLevel.medium,
        evidence="Current hosting provider quote.",
        extracted_numbers=[50, 100],
        raw_assumption="Assumption: Budget 50 to 100 USD per month.",
    )
    result = fermi._validate_single(assumption)
    assert result.status == ValidationStatus.WARNING
    assert any("Below typical" in flag for flag in result.flags)


def test_heuristic_bounds_timeline_exceeds_max():
    """Timeline > 10 years should warn."""
    fermi = FermiSanityCheck()
    assumption = QuantifiedAssumption(
        assumption_id="test-6",
        question="Project duration?",
        claim="Project spans 10 to 20 years.",
        lower_bound=10 * 365,  # 10 years in days
        upper_bound=20 * 365,  # 20 years in days
        unit="days",
        confidence=ConfidenceLevel.medium,
        evidence="Long-term infrastructure project.",
        extracted_numbers=[3650, 7300],
        raw_assumption="Assumption: Project spans 10 to 20 years.",
    )
    result = fermi._validate_single(assumption)
    assert result.status == ValidationStatus.WARNING
    assert any("Exceeds typical" in flag for flag in result.flags)


def test_warning_status_with_wide_span():
    """Span ratio between 50× and 100× should warn but pass."""
    fermi = FermiSanityCheck()
    assumption = QuantifiedAssumption(
        assumption_id="test-7",
        question="Cost estimate?",
        claim="Budget is 1 million to 75 million USD.",
        lower_bound=1_000_000,
        upper_bound=75_000_000,
        unit="usd",
        confidence=ConfidenceLevel.medium,
        evidence="Range based on project scope uncertainty.",
        extracted_numbers=[1_000_000, 75_000_000],
        raw_assumption="Assumption: Budget is 1 million to 75 million USD.",
    )
    result = fermi._validate_single(assumption)
    assert result.status == ValidationStatus.WARNING
    assert any("wide" in flag.lower() for flag in result.flags)


def test_team_size_heuristic():
    """Team size estimates should respect 1-1000 heuristic."""
    fermi = FermiSanityCheck()
    
    # Valid team size
    valid = QuantifiedAssumption(
        assumption_id="test-8a",
        question="Team size?",
        claim="Team of 5 to 15 engineers.",
        lower_bound=5,
        upper_bound=15,
        unit="engineers",
        confidence=ConfidenceLevel.high,
        evidence="HR planning document.",
        extracted_numbers=[5, 15],
        raw_assumption="Assumption: Team of 5 to 15 engineers.",
    )
    result = fermi._validate_single(valid)
    assert result.status == ValidationStatus.PASSED
    
    # Team exceeding heuristic
    oversized = QuantifiedAssumption(
        assumption_id="test-8b",
        question="Team size?",
        claim="5000 to 10000 people needed.",
        lower_bound=5000,
        upper_bound=10000,
        unit="people",
        confidence=ConfidenceLevel.low,
        evidence="Rough estimate for mass hiring.",
        extracted_numbers=[5000, 10000],
        raw_assumption="Assumption: 5000 to 10000 people needed.",
    )
    result = fermi._validate_single(oversized)
    assert result.status == ValidationStatus.WARNING
    assert any("Exceeds typical" in flag for flag in result.flags)


def test_validation_report_aggregation():
    """Validate that ValidationReport correctly aggregates results."""
    fermi = FermiSanityCheck()
    
    assumptions = [
        # Passed
        QuantifiedAssumption(
            assumption_id="a1",
            question="Q1",
            claim="Budget 5 to 7 million USD.",
            lower_bound=5_000_000,
            upper_bound=7_000_000,
            unit="usd",
            confidence=ConfidenceLevel.high,
            evidence="Approved.",
            extracted_numbers=[5_000_000, 7_000_000],
            raw_assumption="Assumption: Budget 5 to 7 million USD.",
        ),
        # Failed (wide span)
        QuantifiedAssumption(
            assumption_id="a2",
            question="Q2",
            claim="Cost 1k to 100m.",
            lower_bound=1_000,
            upper_bound=100_000_000,
            unit="usd",
            confidence=ConfidenceLevel.low,
            evidence="No source.",
            extracted_numbers=[1_000, 100_000_000],
            raw_assumption="Assumption: Cost 1k to 100m.",
        ),
        # Skipped (qualitative)
        QuantifiedAssumption(
            assumption_id="a3",
            question="Q3",
            claim="Team is committed.",
            lower_bound=None,
            upper_bound=None,
            unit=None,
            confidence=ConfidenceLevel.high,
            evidence="CEO said so.",
            extracted_numbers=[],
            raw_assumption="Assumption: Team is committed.",
        ),
    ]
    
    report = fermi.validate(assumptions)
    
    assert report.total_assumptions == 3
    assert report.passed == 1
    assert report.failed == 1
    assert report.skipped == 1
    assert report.pass_rate == 50.0  # 1 passed out of 2 valid
