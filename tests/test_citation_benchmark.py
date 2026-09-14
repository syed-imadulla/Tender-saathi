"""
tests/test_citation_benchmark.py — CITATION RESOLUTION TEST SUITE.

Explicitly tests representative citation forms in isolated benchmark conditions:
- 'IS 15778:2007' (unspaced with year)
- 'IS 15778 : 2007' (spaced with year)
- 'IS 15778' (base standard number without year)
- 'IS 1554 (Part 1):1988' (part-specific standard)
- 'IS/ISO 9001:2015' (ISO adoption compound)
- 'IS/IEC 61439-5:2014' (IEC compound with part delimiter)
- 'SP 30:2023' (Special Publication)

Measures:
- Resolver precision
- Resolver recall
- False-positive identifier matches
- Compound identifier correctness
"""

import pytest
from typing import List, Dict, Any
from src.catalogue.provider import get_default_catalogue_provider
from src.citation_resolver import ExactCitationResolver, ResolvedCitation


@pytest.fixture(scope="module")
def resolver():
    provider = get_default_catalogue_provider("data/catalogue/bis_catalogue.db")
    return ExactCitationResolver(provider)


CITATION_BENCHMARK_CASES = [
    {
        "citation": "IS 15778:2007",
        "expected_canonical_id": "IS-15778-2007",
        "expected_standard_number": "IS 15778 : 2007",
        "category": "unspaced_with_year",
        "is_compound": False
    },
    {
        "citation": "IS 15778 : 2007",
        "expected_canonical_id": "IS-15778-2007",
        "expected_standard_number": "IS 15778 : 2007",
        "category": "spaced_with_year",
        "is_compound": False
    },
    {
        "citation": "IS 15778",
        "expected_canonical_id": "IS-15778-2007",
        "expected_standard_number": "IS 15778 : 2007",
        "category": "base_number_without_year",
        "is_compound": False
    },
    {
        "citation": "IS 1554 (Part 1):1988",
        "expected_canonical_id": "IS-1554-Part-1-1988",
        "expected_standard_number": "IS 1554 (Part 1) : 1988",
        "category": "part_specific",
        "is_compound": False
    },
    {
        "citation": "IS/ISO 9001:2015",
        "expected_canonical_id": "IS-ISO-9001-2015",
        "expected_standard_number": "IS/ISO 9001 : 2015",
        "category": "iso_adoption",
        "is_compound": True
    },
    {
        "citation": "IS/IEC 61439-5:2014",
        "expected_canonical_id": "IS-IEC-61439-Part-5-2014",
        "expected_standard_number": "IS/IEC 61439 (Part 5) : 2014",
        "category": "iec_compound",
        "is_compound": True
    },
    {
        "citation": "SP 30:2023",
        "expected_canonical_id": "SP-30-2023",
        "expected_standard_number": "SP 30 : 2023",
        "category": "special_publication",
        "is_compound": True
    }
]


def test_citation_resolution_benchmark_metrics(resolver):
    """
    Executes the CITATION RESOLUTION TEST SUITE and verifies:
    - 100% precision (no incorrect standard resolved)
    - 100% recall (all representative citations resolved)
    - 0% false positives
    - 100% compound identifier preservation
    """
    total_cases = len(CITATION_BENCHMARK_CASES)
    resolved_count = 0
    correct_count = 0
    false_positives = 0
    compound_correct = 0
    total_compounds = sum(1 for c in CITATION_BENCHMARK_CASES if c["is_compound"])

    for case in CITATION_BENCHMARK_CASES:
        cit = case["citation"]
        res = resolver.resolve_citation(cit)
        
        if res is not None:
            resolved_count += 1
            if res.canonical_id == case["expected_canonical_id"]:
                correct_count += 1
                if case["is_compound"]:
                    compound_correct += 1
            else:
                false_positives += 1
        else:
            # Unresolved citation
            pass

    precision = (correct_count / resolved_count) * 100.0 if resolved_count > 0 else 0.0
    recall = (correct_count / total_cases) * 100.0
    false_positive_rate = (false_positives / total_cases) * 100.0
    compound_acc = (compound_correct / total_compounds) * 100.0 if total_compounds > 0 else 0.0

    print("\n--- CITATION RESOLUTION TEST SUITE METRICS ---")
    print(f"Total Cases: {total_cases}")
    print(f"Resolver Precision: {precision:.1f}%")
    print(f"Resolver Recall: {recall:.1f}%")
    print(f"False-Positive Identifier Matches: {false_positive_rate:.1f}%")
    print(f"Compound Identifier Correctness: {compound_acc:.1f}%")

    assert precision == 100.0, f"Expected 100.0% precision, got {precision}%"
    assert recall == 100.0, f"Expected 100.0% recall, got {recall}%"
    assert false_positives == 0, f"Expected 0 false positives, got {false_positives}"
    assert compound_acc == 100.0, f"Expected 100.0% compound accuracy, got {compound_acc}%"
