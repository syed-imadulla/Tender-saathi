"""
src/precedence — Multi-Requirement Conflict Resolution & Standards Precedence Engine
"""

from src.corpus.semantics import (
    CrossRequirementConflictState,
    CROSS_CONFLICT_STATE_DESCRIPTIONS
)
from src.precedence.conflict_engine import (
    CrossRequirementFinding,
    CrossRequirementAnalysisResult,
    CrossRequirementConflictEngine
)

__all__ = [
    "CrossRequirementConflictState",
    "CROSS_CONFLICT_STATE_DESCRIPTIONS",
    "CrossRequirementFinding",
    "CrossRequirementAnalysisResult",
    "CrossRequirementConflictEngine"
]
