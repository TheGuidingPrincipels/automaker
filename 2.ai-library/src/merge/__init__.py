# src/merge/__init__.py
"""
Merge support for REFINEMENT mode only.

Provides:
- MergeDetector: Find potential merge candidates
- MergeProposer: Create merge proposals using AI
- MergeVerifier: Verify no information is lost in merges
"""

from .detector import MergeDetector, MergeCandidate
from .proposer import MergeProposer, MergeProposal
from .verifier import MergeVerifier, VerificationResult

__all__ = [
    "MergeDetector",
    "MergeCandidate",
    "MergeProposer",
    "MergeProposal",
    "MergeVerifier",
    "VerificationResult",
]
