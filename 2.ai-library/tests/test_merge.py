# tests/test_merge.py
"""Tests for merge support module."""

import pytest
from pathlib import Path

from src.merge.detector import MergeDetector, MergeCandidate
from src.merge.verifier import MergeVerifier, VerificationResult, VerificationStatus
from src.library.manifest import LibraryManifest


class TestMergeCandidate:
    """Tests for MergeCandidate dataclass."""

    def test_create_merge_candidate(self):
        """Create a merge candidate with all fields."""
        candidate = MergeCandidate(
            block_id="block_1",
            target_file="library/auth/jwt.md",
            target_section="Token Validation",
            target_content="Existing content about JWT validation...",
            similarity_score=0.65,
            overlap_phrases=["jwt token", "validation"],
            merge_reasoning="Moderate topic overlap (65%)",
        )

        assert candidate.block_id == "block_1"
        assert candidate.target_file == "library/auth/jwt.md"
        assert candidate.target_section == "Token Validation"
        assert candidate.similarity_score == 0.65
        assert len(candidate.overlap_phrases) == 2


class TestMergeDetector:
    """Tests for MergeDetector class."""

    @pytest.fixture
    def detector(self, tmp_path):
        """Create a MergeDetector instance."""
        return MergeDetector(
            library_path=str(tmp_path),
            similarity_threshold=0.3,
            min_phrase_overlap=1,
        )

    @pytest.fixture
    def library_with_files(self, tmp_path):
        """Create a temporary library with files."""
        # Create library structure
        auth_dir = tmp_path / "auth"
        auth_dir.mkdir()

        # Create a file with content
        jwt_file = auth_dir / "jwt.md"
        jwt_file.write_text(
            """# JWT Authentication

## Token Validation

JWT tokens must be validated on every request.
Check the signature, expiration, and issuer claims.

## Token Generation

Generate tokens with appropriate claims and expiration.
"""
        )

        db_dir = tmp_path / "database"
        db_dir.mkdir()

        postgres_file = db_dir / "postgres.md"
        postgres_file.write_text(
            """# PostgreSQL

## Connection Pooling

Use connection pooling for performance.
Configure pool size based on workload.
"""
        )

        return tmp_path

    def test_extract_phrases_basic(self, detector):
        """Extract phrases from basic text."""
        text = "JWT tokens must be validated on every request"
        phrases = detector._extract_phrases(text)

        assert len(phrases) > 0
        # Should find meaningful phrases
        assert any("token" in p or "valid" in p for p in phrases)

    def test_extract_phrases_filters_common(self, detector):
        """Extract phrases filters common phrases."""
        text = "The cat sat on the mat"
        phrases = detector._extract_phrases(text)

        # Should filter out phrases starting with common words
        assert not any(p.startswith("the ") for p in phrases)

    def test_is_common_phrase(self, detector):
        """Check common phrase detection."""
        assert detector._is_common_phrase("the") is True
        assert detector._is_common_phrase("is a") is True
        assert detector._is_common_phrase("jwt token validation") is False

    def test_compute_similarity_overlap(self, detector):
        """Compute similarity with overlapping phrases."""
        source = {"jwt token", "validation request", "secure auth"}
        target = {"jwt token", "validation request", "different phrase"}

        similarity, overlap = detector._compute_similarity(source, target)

        assert similarity > 0
        assert "jwt token" in overlap
        assert "validation request" in overlap

    def test_compute_similarity_no_overlap(self, detector):
        """Compute similarity with no overlap."""
        source = {"apple", "banana"}
        target = {"cherry", "orange"}

        similarity, overlap = detector._compute_similarity(source, target)

        assert similarity == 0.0
        assert overlap == []

    def test_compute_similarity_empty(self, detector):
        """Compute similarity with empty sets."""
        similarity, overlap = detector._compute_similarity(set(), {"word"})
        assert similarity == 0.0
        assert overlap == []

    @pytest.mark.asyncio
    async def test_find_merge_candidates_strict_mode(self, detector):
        """Merge candidates not found in STRICT mode."""
        block = {
            "id": "block_1",
            "content": "JWT tokens should be validated",
            "heading_path": ["Auth"],
        }
        library_context = {"categories": []}

        candidates = await detector.find_merge_candidates(
            block=block,
            library_context=library_context,
            content_mode="strict",
        )

        # STRICT mode should return no candidates
        assert candidates == []

    @pytest.mark.asyncio
    async def test_manifest_routing_context_includes_file_paths(self, library_with_files):
        """LibraryManifest.get_routing_context must include per-file `path` values."""
        manifest = LibraryManifest(library_path=str(library_with_files))
        context = await manifest.get_routing_context()

        files = []

        def collect(categories):
            for cat in categories:
                files.extend(cat.get("files", []))
                collect(cat.get("subcategories", []))

        collect(context.get("categories", []))

        assert files
        assert all("path" in f for f in files)

    @pytest.mark.asyncio
    async def test_extract_sections(self, detector):
        """Extract sections from markdown content."""
        content = """# Main Title

Introduction text.

## Section One

Content of section one.

## Section Two

Content of section two.
"""
        sections = await detector._extract_sections(content)

        assert "Main Title" in sections
        assert "Section One" in sections
        assert "Section Two" in sections
        assert "section one" in sections["Section One"].lower()

    def test_generate_reasoning_strong(self, detector):
        """Generate reasoning for strong overlap."""
        reasoning = detector._generate_reasoning(
            ["jwt token", "validation"], 0.6
        )

        assert "strong" in reasoning.lower()
        assert "jwt token" in reasoning

    def test_generate_reasoning_moderate(self, detector):
        """Generate reasoning for moderate overlap."""
        reasoning = detector._generate_reasoning(["auth"], 0.4)

        assert "moderate" in reasoning.lower()

    def test_generate_reasoning_weak(self, detector):
        """Generate reasoning for weak overlap."""
        reasoning = detector._generate_reasoning([], 0.2)

        assert "weak" in reasoning.lower()


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_create_passed_result(self):
        """Create a passed verification result."""
        result = VerificationResult(
            status=VerificationStatus.PASSED,
            confidence=0.95,
            details="All content preserved",
        )

        assert result.status == VerificationStatus.PASSED
        assert result.confidence == 0.95
        assert result.missing_from_original == []
        assert result.missing_from_source == []

    def test_create_failed_result(self):
        """Create a failed verification result."""
        result = VerificationResult(
            status=VerificationStatus.FAILED,
            missing_from_original=["important phrase one"],
            missing_from_source=["critical detail"],
            confidence=0.3,
            details="Information loss detected",
        )

        assert result.status == VerificationStatus.FAILED
        assert len(result.missing_from_original) == 1
        assert len(result.missing_from_source) == 1


class TestMergeVerifier:
    """Tests for MergeVerifier class."""

    @pytest.fixture
    def verifier(self):
        """Create a MergeVerifier instance."""
        return MergeVerifier(confidence_threshold=0.9)

    def test_normalize_text(self, verifier):
        """Normalize text removes formatting."""
        text = "# Heading\n\n**Bold** and `code`"
        normalized = verifier._normalize_text(text)

        assert "heading" in normalized
        assert "bold" in normalized
        assert "#" not in normalized
        assert "**" not in normalized

    def test_extract_key_phrases(self, verifier):
        """Extract key phrases from text."""
        text = "jwt tokens must be validated on every request for security"
        phrases = verifier._extract_key_phrases(text)

        assert len(phrases) > 0

    def test_is_significant_phrase(self, verifier):
        """Check significant phrase detection."""
        # Too short
        assert verifier._is_significant_phrase("a b") is False

        # Starts with common word
        assert verifier._is_significant_phrase("the quick brown fox") is False

        # Valid significant phrase
        assert verifier._is_significant_phrase("validation must happen") is True

    def test_extract_key_values_numbers(self, verifier):
        """Extract key values finds numbers."""
        text = "Set timeout to 30 seconds and pool size to 100"
        values = verifier._extract_key_values(text)

        assert any("30" in v for v in values)
        assert any("100" in v for v in values)

    def test_extract_key_values_urls(self, verifier):
        """Extract key values finds URLs."""
        text = "Visit https://example.com/api for docs"
        values = verifier._extract_key_values(text)

        assert any("https://example.com" in v for v in values)

    def test_extract_key_values_identifiers(self, verifier):
        """Extract key values finds code identifiers."""
        text = "Use getUserData and process_request functions"
        values = verifier._extract_key_values(text)

        assert "getUserData" in values
        assert "process_request" in values

    def test_verify_no_loss_identical(self, verifier):
        """Verify identical content passes."""
        content = "JWT tokens must be validated"

        result = verifier.verify_no_information_loss(
            original_content=content,
            source_content=content,
            merged_content=content + " " + content,
        )

        assert result.status == VerificationStatus.PASSED
        assert result.confidence >= 0.9

    def test_verify_no_loss_complete_merge(self, verifier):
        """Verify complete merge passes."""
        original = "JWT tokens are secure authentication method"
        source = "Database connections use connection pooling"
        merged = f"{original}\n\n{source}"

        result = verifier.verify_no_information_loss(
            original_content=original,
            source_content=source,
            merged_content=merged,
        )

        assert result.status == VerificationStatus.PASSED

    def test_verify_detects_missing_original(self, verifier):
        """Verify detects missing content from original."""
        original = "Critical security configuration must use SSL/TLS encryption"
        source = "Simple note"
        merged = source  # Original is completely missing

        result = verifier.verify_no_information_loss(
            original_content=original,
            source_content=source,
            merged_content=merged,
        )

        # Should detect missing content
        assert result.status in (
            VerificationStatus.FAILED,
            VerificationStatus.NEEDS_REVIEW,
        )
        assert result.confidence < 0.9

    def test_verify_detects_missing_source(self, verifier):
        """Verify detects missing content from source."""
        original = "Simple note"
        source = "Critical database migration must preserve foreign keys"
        merged = original  # Source is completely missing

        result = verifier.verify_no_information_loss(
            original_content=original,
            source_content=source,
            merged_content=merged,
        )

        # Should detect missing content
        assert result.status in (
            VerificationStatus.FAILED,
            VerificationStatus.NEEDS_REVIEW,
        )

    def test_partial_match_high_overlap(self, verifier):
        """Partial match detects high word overlap."""
        assert verifier._partial_match(
            "jwt token validation",
            "the jwt token validation process",
            threshold=0.7,
        ) is True

    def test_partial_match_low_overlap(self, verifier):
        """Partial match rejects low word overlap."""
        assert verifier._partial_match(
            "jwt token validation security",
            "database connection pooling",
            threshold=0.7,
        ) is False

    def test_verify_batch(self, verifier):
        """Verify batch processes multiple verifications."""
        verifications = [
            ("content a", "source a", "content a source a"),
            ("content b", "source b", "content b source b"),
        ]

        results = verifier.verify_batch(verifications)

        assert len(results) == 2
        assert all(isinstance(r, VerificationResult) for r in results)


class TestVerificationStatus:
    """Tests for VerificationStatus enum."""

    def test_all_statuses_defined(self):
        """All verification statuses are defined."""
        assert VerificationStatus.PASSED.value == "passed"
        assert VerificationStatus.FAILED.value == "failed"
        assert VerificationStatus.NEEDS_REVIEW.value == "needs_review"
