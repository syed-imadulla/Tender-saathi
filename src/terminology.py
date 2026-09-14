"""
Module: src/terminology.py
Purpose: Deterministic, domain-grounded engineering terminology mapping for TenderSaathi.

Provides auditable, rule-based expansion of technical acronyms and tender shorthand
into canonical technical descriptors used in Bureau of Indian Standards (BIS) catalogues.

CRITICAL INVARIANTS:
1. Must NOT inject IS numbers or fabricate standard codes.
2. Must NOT use non-deterministic LLM hallucination.
3. Every expansion is explicit, deterministic, auditable, and domain-grounded.
"""

import re
from typing import List, Dict, Set, Tuple


# Canonical Engineering Terminology Dictionary
# Maps common Indian public procurement abbreviations to formal BIS catalogue vocabulary.
TECHNICAL_TERMINOLOGY_MAP: Dict[str, List[str]] = {
    # Electrical Drives & Control
    "vfd": ["variable frequency drive", "adjustable speed electrical power drive systems"],
    "vsd": ["variable speed drive", "adjustable speed power drive"],
    "asd": ["adjustable speed electrical power drive systems"],
    "soft starter": ["reduced voltage ac starter", "motor starter"],
    
    # Power Generation & Storage
    "dg set": ["diesel generator", "generating set", "reciprocating internal combustion engine driven generating set"],
    "dg": ["diesel generator", "generating set"],
    "genset": ["generating set", "diesel engine generator"],
    "ups": ["uninterruptible power system"],
    
    # Cables & Conductors
    "xlpe": ["crosslinked polyethylene", "cross-linked polyethylene"],
    "lt": ["low tension", "working voltages up to and including 1100 volts"],
    "ht": ["high tension", "working voltages exceeding 1100 volts"],
    "ehv": ["extra high voltage", "working voltages exceeding 33 kv"],
    "frls": ["flame retardant low smoke"],
    "fr": ["fire survival", "flame retardant"],
    "pvc insulated": ["polyvinyl chloride insulated"],
    "acsr": ["aluminum conductors steel reinforced"],
    
    # Piping & Civil Materials
    "cpvc": ["chlorinated polyvinyl chloride"],
    "upvc": ["unplasticized polyvinyl chloride"],
    "hdpe": ["high density polyethylene"],
    "pvc": ["polyvinyl chloride"],
    "di pipe": ["ductile iron pipe", "centrifugally cast ductile iron"],
    "ci pipe": ["cast iron pipe"],
    "ms pipe": ["mild steel pipe"],
    "gi pipe": ["galvanized iron pipe", "galvanized steel pipe"],
    "gi": ["galvanized iron", "galvanized steel"],
    "opc": ["ordinary portland cement"],
    "ppc": ["portland pozzolana cement"],
    "psc": ["portland slag cement"],
    "tmt": ["thermo mechanically treated steel bars"],
    
    # Switchgear & Protection
    "mcb": ["miniature circuit breaker"],
    "mccb": ["moulded case circuit breaker"],
    "acb": ["air circuit breaker"],
    "vcb": ["vacuum circuit breaker"],
    "elcb": ["earth leakage circuit breaker"],
    "rccb": ["residual current circuit breaker"],
    "rcbo": ["residual current breaker with overcurrent protection"],
    "db": ["distribution board", "switchboard"],
    "feeder pillar": ["distribution pillar", "outdoor distribution pillar"],
    
    # Pumps & Rotodynamics
    "submersible pump": ["submersible pumpsets", "submersible motor pumpset"],
    "centrifugal pump": ["rotodynamic special purpose pumps", "centrifugal pumps for clear cold water"],
    "mono block": ["monoset pump", "monobloc pump"],
}


class TechnicalTerminologyNormalizer:
    """
    Applies deterministic technical synonym expansion to requirement queries
    to bridge vocabulary mismatch between tender shorthand and BIS standards titles.
    """

    def __init__(self, mapping: Dict[str, List[str]] = None):
        self.mapping = mapping or TECHNICAL_TERMINOLOGY_MAP
        # Compile case-insensitive word-boundary regexes
        self._compiled_patterns: List[Tuple[re.Pattern, str, List[str]]] = []
        for term, expansions in self.mapping.items():
            pattern = re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE)
            self._compiled_patterns.append((pattern, term, expansions))

    def extract_expansions(self, text: str) -> Dict[str, List[str]]:
        """
        Identifies all technical abbreviations in the text and returns their expansions.
        Returns: {matched_term: [canonical_expansions]}
        """
        if not text:
            return {}

        results: Dict[str, List[str]] = {}
        for pattern, term, expansions in self._compiled_patterns:
            if pattern.search(text):
                results[term] = expansions
        return results

    def build_expanded_query(self, text: str, max_expansions_per_term: int = 2) -> str:
        """
        Returns the original query augmented with domain-grounded technical expansions.
        Preserves original query as the primary anchor.
        """
        expansions_map = self.extract_expansions(text)
        if not expansions_map:
            return text

        added_tokens: Set[str] = set()
        expansion_clauses: List[str] = []
        for term, exp_list in expansions_map.items():
            for exp in exp_list[:max_expansions_per_term]:
                # Avoid adding words already in the original query
                words = [w for w in exp.split() if w.lower() not in text.lower() and w.lower() not in added_tokens]
                if words:
                    added_tokens.update(w.lower() for w in words)
                    expansion_clauses.append(" ".join(words))

        if expansion_clauses:
            return f"{text} ({' '.join(expansion_clauses)})"
        return text
