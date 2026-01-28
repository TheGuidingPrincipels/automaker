"""
Predefined knowledge domains for the Knowledge Server.

This module defines the 13 core areas that organize knowledge concepts.
Custom areas are allowed but these provide a recommended taxonomy.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Area:
    """Represents a knowledge area/domain."""

    slug: str           # Unique identifier (kebab-case)
    label: str          # Human-readable name
    description: str    # Brief description for UI tooltips

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "slug": self.slug,
            "label": self.label,
            "description": self.description
        }


# The 13 predefined areas
PREDEFINED_AREAS: List[Area] = [
    Area(
        slug="coding-development",
        label="Coding & Development",
        description="Programming, APIs, frameworks, software engineering"
    ),
    Area(
        slug="ai-llms",
        label="AI & LLMs",
        description="Machine learning, prompts, agents, neural networks"
    ),
    Area(
        slug="productivity",
        label="Productivity",
        description="Time management, workflows, efficiency, tools"
    ),
    Area(
        slug="learning",
        label="Learning",
        description="Memory, retention, mind maps, study techniques"
    ),
    Area(
        slug="business",
        label="Business",
        description="Strategy, sales, entrepreneurship, management"
    ),
    Area(
        slug="health",
        label="Health",
        description="Exercise, nutrition, sleep, wellness"
    ),
    Area(
        slug="mindset",
        label="Mindset",
        description="Psychology, personal growth, habits, motivation"
    ),
    Area(
        slug="marketing",
        label="Marketing",
        description="Copywriting, funnels, content, branding"
    ),
    Area(
        slug="video-content",
        label="Video & Content",
        description="Video production, editing, streaming, media"
    ),
    Area(
        slug="spirituality",
        label="Spirituality",
        description="Spiritual practices, meditation, consciousness"
    ),
    Area(
        slug="philosophy",
        label="Philosophy",
        description="Ethics, logic, metaphysics, epistemology"
    ),
    Area(
        slug="history",
        label="History",
        description="Historical events, civilizations, biographies"
    ),
    Area(
        slug="physics",
        label="Physics",
        description="Classical mechanics, quantum physics, thermodynamics"
    ),
]

# Quick lookup set for validation
AREA_SLUGS: set[str] = {area.slug for area in PREDEFINED_AREAS}

# Mapping from slug to Area object
AREAS_BY_SLUG: dict[str, Area] = {area.slug: area for area in PREDEFINED_AREAS}


def is_predefined_area(slug: str) -> bool:
    """Check if an area slug is in the predefined list."""
    return slug in AREA_SLUGS


def get_area(slug: str) -> Optional[Area]:
    """Get Area object by slug, or None if not found."""
    return AREAS_BY_SLUG.get(slug)


def get_all_areas() -> List[dict]:
    """Get all predefined areas as dictionaries."""
    return [area.to_dict() for area in PREDEFINED_AREAS]
