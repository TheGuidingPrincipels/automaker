"""Cleanup mode settings for AI-assisted cleanup."""

from enum import Enum


class CleanupModeSetting(str, Enum):
    """User-selectable cleanup aggressiveness modes."""

    CONSERVATIVE = "conservative"
    """Only suggest discard for obvious noise. High confidence required (0.85+)."""

    BALANCED = "balanced"
    """Smart suggestions based on all criteria. Default mode. (0.70+ confidence)"""

    AGGRESSIVE = "aggressive"
    """Actively flag time-sensitive and ephemeral content. (0.55+ confidence)"""

    @property
    def confidence_threshold(self) -> float:
        """Minimum confidence required to suggest discard."""
        thresholds = {
            CleanupModeSetting.CONSERVATIVE: 0.85,
            CleanupModeSetting.BALANCED: 0.70,
            CleanupModeSetting.AGGRESSIVE: 0.55,
        }
        return thresholds[self]

    @property
    def description(self) -> str:
        """Human-readable description of the mode."""
        descriptions = {
            CleanupModeSetting.CONSERVATIVE: "Keep more - only suggest discard for obvious noise",
            CleanupModeSetting.BALANCED: "Balanced - smart suggestions based on content signals",
            CleanupModeSetting.AGGRESSIVE: "Discard more - actively flag time-sensitive content",
        }
        return descriptions[self]
