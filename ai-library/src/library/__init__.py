"""Library management for organizing knowledge files."""

from .categories import CategoryManager
from .scanner import LibraryScanner
from .manifest import LibraryManifest
from .candidates import (
    CandidateFinder,
    CandidateMatch,
    LexicalCandidateFinder,
    get_candidate_finder,
)
from .candidates_vector import VectorCandidateFinder

__all__ = [
    "CategoryManager",
    "LibraryScanner",
    "LibraryManifest",
    # Candidate finding
    "CandidateFinder",
    "CandidateMatch",
    "LexicalCandidateFinder",
    "VectorCandidateFinder",
    "get_candidate_finder",
]
