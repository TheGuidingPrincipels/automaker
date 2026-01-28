"""
Unit tests for domain configuration.

Tests the Area dataclass, predefined areas, and helper functions
for domain/area validation and lookup.
"""

import pytest
from dataclasses import FrozenInstanceError

from config.domains import (
    Area,
    PREDEFINED_AREAS,
    AREA_SLUGS,
    AREAS_BY_SLUG,
    is_predefined_area,
    get_area,
    get_all_areas,
)


# =============================================================================
# Area Dataclass Tests
# =============================================================================

class TestAreaDataclass:
    """Tests for the Area dataclass."""

    def test_area_initialization(self):
        """Area should initialize with slug, label, and description."""
        area = Area(
            slug="test-area",
            label="Test Area",
            description="A test area for unit testing"
        )

        assert area.slug == "test-area"
        assert area.label == "Test Area"
        assert area.description == "A test area for unit testing"

    def test_area_is_frozen(self):
        """Area dataclass should be immutable (frozen)."""
        area = Area(
            slug="test-area",
            label="Test Area",
            description="A test area"
        )

        with pytest.raises(FrozenInstanceError):
            area.slug = "modified-slug"

    def test_area_equality(self):
        """Two Areas with same attributes should be equal."""
        area1 = Area(slug="test", label="Test", description="Test desc")
        area2 = Area(slug="test", label="Test", description="Test desc")

        assert area1 == area2

    def test_area_inequality(self):
        """Areas with different attributes should not be equal."""
        area1 = Area(slug="test1", label="Test 1", description="Test desc")
        area2 = Area(slug="test2", label="Test 2", description="Test desc")

        assert area1 != area2

    def test_area_to_dict(self):
        """to_dict() should return correct dictionary representation."""
        area = Area(
            slug="coding-development",
            label="Coding & Development",
            description="Programming, APIs, frameworks"
        )

        result = area.to_dict()

        assert isinstance(result, dict)
        assert result["slug"] == "coding-development"
        assert result["label"] == "Coding & Development"
        assert result["description"] == "Programming, APIs, frameworks"
        assert len(result) == 3

    def test_area_to_dict_preserves_special_characters(self):
        """to_dict() should preserve special characters in strings."""
        area = Area(
            slug="ai-llms",
            label="AI & LLMs",
            description="Machine learning, prompts, agents"
        )

        result = area.to_dict()

        assert "&" in result["label"]


# =============================================================================
# PREDEFINED_AREAS Tests
# =============================================================================

class TestPredefinedAreas:
    """Tests for the PREDEFINED_AREAS list."""

    def test_predefined_areas_count(self):
        """Should have exactly 13 predefined areas."""
        assert len(PREDEFINED_AREAS) == 13

    def test_predefined_areas_are_area_instances(self):
        """All items in PREDEFINED_AREAS should be Area instances."""
        for area in PREDEFINED_AREAS:
            assert isinstance(area, Area)

    def test_predefined_areas_have_unique_slugs(self):
        """All predefined areas should have unique slugs."""
        slugs = [area.slug for area in PREDEFINED_AREAS]
        assert len(slugs) == len(set(slugs))

    def test_predefined_areas_slugs_are_kebab_case(self):
        """All area slugs should be kebab-case (lowercase with hyphens)."""
        for area in PREDEFINED_AREAS:
            assert area.slug == area.slug.lower(), f"Slug '{area.slug}' is not lowercase"
            assert " " not in area.slug, f"Slug '{area.slug}' contains spaces"
            assert "_" not in area.slug, f"Slug '{area.slug}' contains underscores"

    def test_predefined_areas_have_labels(self):
        """All predefined areas should have non-empty labels."""
        for area in PREDEFINED_AREAS:
            assert area.label, f"Area '{area.slug}' has empty label"
            assert len(area.label) > 0

    def test_predefined_areas_have_descriptions(self):
        """All predefined areas should have non-empty descriptions."""
        for area in PREDEFINED_AREAS:
            assert area.description, f"Area '{area.slug}' has empty description"
            assert len(area.description) > 0

    def test_expected_areas_are_present(self):
        """All expected core areas should be in the predefined list."""
        expected_slugs = [
            "coding-development",
            "ai-llms",
            "productivity",
            "learning",
            "business",
            "health",
            "mindset",
            "marketing",
            "video-content",
            "spirituality",
            "philosophy",
            "history",
            "physics",
        ]

        actual_slugs = [area.slug for area in PREDEFINED_AREAS]

        for expected in expected_slugs:
            assert expected in actual_slugs, f"Expected area '{expected}' not found"

    def test_predefined_areas_is_immutable_list(self):
        """PREDEFINED_AREAS should be a list (content check, not mutation test)."""
        assert isinstance(PREDEFINED_AREAS, list)


# =============================================================================
# AREA_SLUGS Set Tests
# =============================================================================

class TestAreaSlugs:
    """Tests for the AREA_SLUGS set."""

    def test_area_slugs_is_set(self):
        """AREA_SLUGS should be a set."""
        assert isinstance(AREA_SLUGS, set)

    def test_area_slugs_count_matches_predefined_areas(self):
        """AREA_SLUGS should have same count as PREDEFINED_AREAS."""
        assert len(AREA_SLUGS) == len(PREDEFINED_AREAS)

    def test_area_slugs_contains_all_predefined_slugs(self):
        """AREA_SLUGS should contain all slugs from PREDEFINED_AREAS."""
        for area in PREDEFINED_AREAS:
            assert area.slug in AREA_SLUGS

    def test_area_slugs_lookup_is_efficient(self):
        """Set membership check should work correctly."""
        assert "coding-development" in AREA_SLUGS
        assert "nonexistent-area" not in AREA_SLUGS


# =============================================================================
# AREAS_BY_SLUG Dict Tests
# =============================================================================

class TestAreasBySlug:
    """Tests for the AREAS_BY_SLUG dictionary."""

    def test_areas_by_slug_is_dict(self):
        """AREAS_BY_SLUG should be a dictionary."""
        assert isinstance(AREAS_BY_SLUG, dict)

    def test_areas_by_slug_count_matches_predefined_areas(self):
        """AREAS_BY_SLUG should have same count as PREDEFINED_AREAS."""
        assert len(AREAS_BY_SLUG) == len(PREDEFINED_AREAS)

    def test_areas_by_slug_keys_are_strings(self):
        """All keys in AREAS_BY_SLUG should be strings."""
        for key in AREAS_BY_SLUG.keys():
            assert isinstance(key, str)

    def test_areas_by_slug_values_are_areas(self):
        """All values in AREAS_BY_SLUG should be Area instances."""
        for value in AREAS_BY_SLUG.values():
            assert isinstance(value, Area)

    def test_areas_by_slug_correct_mapping(self):
        """AREAS_BY_SLUG should map slugs to correct Area objects."""
        for area in PREDEFINED_AREAS:
            assert AREAS_BY_SLUG[area.slug] == area

    def test_areas_by_slug_lookup(self):
        """Dictionary lookup should return correct Area."""
        area = AREAS_BY_SLUG["coding-development"]

        assert area.slug == "coding-development"
        assert area.label == "Coding & Development"


# =============================================================================
# is_predefined_area() Function Tests
# =============================================================================

class TestIsPredefinedArea:
    """Tests for the is_predefined_area() function."""

    def test_returns_true_for_valid_slug(self):
        """Should return True for a valid predefined slug."""
        assert is_predefined_area("coding-development") is True
        assert is_predefined_area("ai-llms") is True
        assert is_predefined_area("physics") is True

    def test_returns_false_for_invalid_slug(self):
        """Should return False for an invalid slug."""
        assert is_predefined_area("nonexistent-area") is False
        assert is_predefined_area("random-slug") is False

    def test_returns_false_for_empty_string(self):
        """Should return False for an empty string."""
        assert is_predefined_area("") is False

    def test_is_case_sensitive(self):
        """Slug matching should be case-sensitive."""
        assert is_predefined_area("coding-development") is True
        assert is_predefined_area("Coding-Development") is False
        assert is_predefined_area("CODING-DEVELOPMENT") is False

    def test_returns_false_for_partial_match(self):
        """Should return False for partial slug matches."""
        assert is_predefined_area("coding") is False
        assert is_predefined_area("development") is False
        assert is_predefined_area("coding-dev") is False

    def test_returns_false_for_slug_with_whitespace(self):
        """Should return False for slugs with whitespace."""
        assert is_predefined_area(" coding-development") is False
        assert is_predefined_area("coding-development ") is False
        assert is_predefined_area(" coding-development ") is False

    def test_all_predefined_areas_are_valid(self):
        """All slugs from PREDEFINED_AREAS should return True."""
        for area in PREDEFINED_AREAS:
            assert is_predefined_area(area.slug) is True


# =============================================================================
# get_area() Function Tests
# =============================================================================

class TestGetArea:
    """Tests for the get_area() function."""

    def test_returns_area_for_valid_slug(self):
        """Should return Area object for a valid slug."""
        area = get_area("coding-development")

        assert area is not None
        assert isinstance(area, Area)
        assert area.slug == "coding-development"
        assert area.label == "Coding & Development"

    def test_returns_none_for_invalid_slug(self):
        """Should return None for an invalid slug."""
        area = get_area("nonexistent-area")

        assert area is None

    def test_returns_none_for_empty_string(self):
        """Should return None for an empty string."""
        area = get_area("")

        assert area is None

    def test_is_case_sensitive(self):
        """Slug lookup should be case-sensitive."""
        assert get_area("ai-llms") is not None
        assert get_area("AI-LLMS") is None
        assert get_area("Ai-Llms") is None

    def test_returns_correct_area_for_each_predefined(self):
        """Should return correct Area for each predefined slug."""
        for expected_area in PREDEFINED_AREAS:
            retrieved_area = get_area(expected_area.slug)

            assert retrieved_area is not None
            assert retrieved_area == expected_area

    def test_returns_same_instance_as_predefined_list(self):
        """Retrieved Area should be the same instance as in PREDEFINED_AREAS."""
        area = get_area("productivity")
        expected = next(a for a in PREDEFINED_AREAS if a.slug == "productivity")

        assert area is expected


# =============================================================================
# get_all_areas() Function Tests
# =============================================================================

class TestGetAllAreas:
    """Tests for the get_all_areas() function."""

    def test_returns_list(self):
        """Should return a list."""
        result = get_all_areas()

        assert isinstance(result, list)

    def test_returns_correct_count(self):
        """Should return all 13 predefined areas."""
        result = get_all_areas()

        assert len(result) == 13

    def test_returns_list_of_dicts(self):
        """Should return a list of dictionaries."""
        result = get_all_areas()

        for item in result:
            assert isinstance(item, dict)

    def test_each_dict_has_required_keys(self):
        """Each dictionary should have slug, label, and description keys."""
        result = get_all_areas()

        for item in result:
            assert "slug" in item
            assert "label" in item
            assert "description" in item
            assert len(item) == 3

    def test_dict_values_match_predefined_areas(self):
        """Dictionary values should match the predefined areas."""
        result = get_all_areas()
        result_by_slug = {item["slug"]: item for item in result}

        for area in PREDEFINED_AREAS:
            area_dict = result_by_slug.get(area.slug)
            assert area_dict is not None
            assert area_dict["label"] == area.label
            assert area_dict["description"] == area.description

    def test_returns_new_list_each_call(self):
        """Should return a new list on each call (not a reference)."""
        result1 = get_all_areas()
        result2 = get_all_areas()

        assert result1 is not result2
        assert result1 == result2

    def test_preserves_order(self):
        """Should preserve the order of predefined areas."""
        result = get_all_areas()

        for i, area in enumerate(PREDEFINED_AREAS):
            assert result[i]["slug"] == area.slug


# =============================================================================
# Integration / Cross-Module Tests
# =============================================================================

class TestDomainConfigIntegration:
    """Integration tests across domain configuration components."""

    def test_area_slugs_and_areas_by_slug_are_consistent(self):
        """AREA_SLUGS and AREAS_BY_SLUG should contain the same slugs."""
        assert AREA_SLUGS == set(AREAS_BY_SLUG.keys())

    def test_is_predefined_area_uses_area_slugs(self):
        """is_predefined_area should be consistent with AREA_SLUGS."""
        for slug in AREA_SLUGS:
            assert is_predefined_area(slug) is True

        for slug in ["fake", "not-real", "test"]:
            assert slug not in AREA_SLUGS
            assert is_predefined_area(slug) is False

    def test_get_area_uses_areas_by_slug(self):
        """get_area should be consistent with AREAS_BY_SLUG."""
        for slug, area in AREAS_BY_SLUG.items():
            assert get_area(slug) == area

    def test_all_components_have_same_count(self):
        """All data structures should have consistent counts."""
        count = 13

        assert len(PREDEFINED_AREAS) == count
        assert len(AREA_SLUGS) == count
        assert len(AREAS_BY_SLUG) == count
        assert len(get_all_areas()) == count
