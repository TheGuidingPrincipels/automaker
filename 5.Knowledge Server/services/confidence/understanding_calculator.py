"""
Understanding score calculator for confidence scoring system.

Calculates understanding score from three weighted components:
- Relationship density (40%): How well concept is connected
- Explanation quality (30%): TF-IDF based vocabulary richness
- Metadata completeness (30%): Presence of tags, examples, etc.
"""

import json
import logging
import os
import time
from datetime import datetime

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

from services.confidence.cache_manager import CacheManager
from services.confidence.data_access import DataAccessLayer
from services.confidence.models import Error, ErrorCode, Success
from services.confidence.validation import check_data_completeness


logger = logging.getLogger(__name__)


class TFIDFCorpusManager:
    """Manages TF-IDF vectorizer lifecycle with trigger-based recalculation."""

    def __init__(self, vectorizer_path="services/confidence/cache/tfidf_vectorizer.pkl"):
        self.vectorizer_path = vectorizer_path
        self.metadata_path = vectorizer_path + ".meta.json"
        self.vectorizer = None
        self.last_concept_count = 0
        self.last_recalc_date = None

    def should_recalculate(self, current_concept_count: int) -> bool:
        """Check if corpus recalculation needed."""
        # First initialization - vectorizer must exist as object AND file
        if self.vectorizer is None:
            return True

        if not os.path.exists(self.vectorizer_path):
            return True

        # Growth trigger: 15% increase
        if self.last_concept_count > 0:
            growth_rate = (
                current_concept_count - self.last_concept_count
            ) / self.last_concept_count
            if growth_rate >= 0.15:  # Greater than or equal to 15%
                return True

        # Time trigger: 30 days
        if self.last_recalc_date is not None:
            days_since = (datetime.now() - self.last_recalc_date).days
            if days_since >= 30:  # Greater than or equal to 30 days
                return True

        return False

    async def recalculate_corpus(self, all_explanations: list[str]) -> Success | Error:
        """Fully recalculate TF-IDF vectorizer with entire corpus."""
        try:
            start_time = time.time()

            # Validate corpus
            if not all_explanations or len(all_explanations) == 0:
                return Error(
                    "Cannot recalculate corpus with empty explanations list",
                    ErrorCode.VALIDATION_ERROR,
                )

            # Fit new vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words="english",
                ngram_range=(1, 2),
                min_df=2,  # Ignore words appearing in <2 documents
                max_df=0.8,  # Ignore words appearing in >80% documents
            )
            self.vectorizer.fit(all_explanations)

            # Ensure directory exists (handle empty dirname for relative paths)
            dir_path = os.path.dirname(self.vectorizer_path)
            if dir_path:  # Only create if dirname is not empty
                os.makedirs(dir_path, exist_ok=True)

            # Persist atomically (write temp, then rename)
            temp_path = self.vectorizer_path + ".tmp"
            joblib.dump(self.vectorizer, temp_path)
            os.rename(temp_path, self.vectorizer_path)

            # Update tracking metadata
            self.last_concept_count = len(all_explanations)
            self.last_recalc_date = datetime.now()

            metadata = {
                "last_concept_count": self.last_concept_count,
                "last_recalc_date": self.last_recalc_date.isoformat(),
                "vocabulary_size": len(self.vectorizer.vocabulary_),
                "vectorizer_version": "1.0",
            }
            with open(self.metadata_path, "w") as f:
                json.dump(metadata, f)

            duration = time.time() - start_time
            logger.info(
                "TF-IDF corpus recalculated",
                extra={
                    "corpus_size": len(all_explanations),
                    "vocabulary_size": len(self.vectorizer.vocabulary_),
                    "duration_seconds": duration,
                },
            )

            return Success(f"Recalculated corpus with {len(all_explanations)} concepts")

        except Exception as e:
            logger.error(f"Corpus recalculation failed: {e}")
            return Error(
                f"Corpus recalculation failed: {e!s}",
                ErrorCode.DATABASE_ERROR,
            )

    def load_vectorizer(self) -> Success | Error:
        """Load persisted vectorizer from disk."""
        try:
            if not os.path.exists(self.vectorizer_path):
                return Error("No persisted vectorizer found", ErrorCode.NOT_FOUND)

            self.vectorizer = joblib.load(self.vectorizer_path)

            # Load metadata
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path) as f:
                    metadata = json.load(f)
                    self.last_concept_count = metadata.get("last_concept_count", 0)
                    date_str = metadata.get("last_recalc_date")
                    if date_str:
                        self.last_recalc_date = datetime.fromisoformat(date_str)

            return Success("Vectorizer loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load vectorizer: {e}")
            return Error(
                f"Failed to load vectorizer: {e!s}",
                ErrorCode.DATABASE_ERROR,
            )


class UnderstandingCalculator:
    """Calculate understanding score from relationships, explanation, and metadata"""

    RELATIONSHIP_WEIGHT = 0.40
    EXPLANATION_WEIGHT = 0.30
    METADATA_WEIGHT = 0.30

    def __init__(
        self,
        data_access: DataAccessLayer,
        cache_manager: CacheManager,
        max_relationships: int = 20,
    ):
        self.data_access = data_access
        self.cache = cache_manager
        self.max_relationships = max_relationships

    async def calculate_relationship_density(self, concept_id: str) -> Success | Error:
        """
        Calculate relationship density score (0.0-1.0).

        Formula: connected_concepts / max_possible_connections
        """
        try:
            # Check cache first
            cached_data = await self.cache.get_cached_relationships(concept_id)

            if cached_data:
                relationship_data = cached_data
                logger.debug(f"Using cached relationships for {concept_id}")
            else:
                # Query database
                result = await self.data_access.get_concept_relationships(concept_id)

                if isinstance(result, Error):
                    return result

                relationship_data = result.value

                # Cache for next time
                await self.cache.set_cached_relationships(concept_id, relationship_data)

            # Calculate density
            if self.max_relationships == 0:
                density = 0.0
            else:
                density = min(
                    relationship_data.unique_connections / self.max_relationships,
                    1.0,  # Cap at 1.0
                )

            logger.debug(f"Relationship density for {concept_id}: {density}")
            return Success(density)

        except Exception as e:
            logger.error(f"Relationship density calculation error: {e}")
            return Error(
                f"Failed to calculate relationship density: {e!s}",
                ErrorCode.DATABASE_ERROR,
            )

    # Domain-specific technical terms that should boost scores
    # even when they are short (common CS/tech vocabulary)
    TECHNICAL_TERMS = frozenset({
        # Protocols and standards
        "api", "http", "https", "tcp", "udp", "ip", "dns", "ssl", "tls",
        "ssh", "ftp", "smtp", "rest", "rpc", "grpc", "soap", "mqtt", "amqp",
        # Programming concepts
        "sql", "orm", "mvc", "mvvm", "dom", "css", "html", "xml", "json",
        "yaml", "jwt", "oauth", "cors", "crud", "dry", "yagni", "kiss",
        # Data and databases
        "db", "rdbms", "nosql", "olap", "oltp", "etl", "acid", "cap",
        # Cloud and infrastructure
        "aws", "gcp", "cdn", "vpc", "iam", "k8s", "ci", "cd", "cli", "gui",
        # Languages and frameworks
        "js", "ts", "py", "go", "cpp", "jvm", "sdk", "npm", "pip",
        # AI/ML
        "ai", "ml", "llm", "nlp", "gpu", "tpu", "cnn", "rnn", "gan",
        # General computing
        "cpu", "ram", "ssd", "os", "vm", "io", "uid", "pid", "utf",
        "uri", "url", "urn", "oop", "ddd", "tdd", "bdd", "ioc", "di",
    })

    # Minimum score floor for any non-empty explanation
    MINIMUM_EXPLANATION_SCORE = 0.1

    def calculate_explanation_quality(self, explanation: str) -> float:
        """
        Calculate explanation quality using vocabulary richness heuristic (0.0-1.0).

        Uses word count, uniqueness ratio, and domain-specific term recognition.
        Full TF-IDF corpus fitting is available via TFIDFCorpusManager but
        requires background corpus building (future enhancement for per-query scoring).

        Improvements over basic word counting:
        - Recognizes short technical terms (API, SQL, HTTP, etc.)
        - Applies minimum score floor for any non-empty explanation
        - Provides boost for domain-specific vocabulary

        Returns vocabulary richness score.
        """
        if not explanation or explanation.strip() == "":
            return 0.0

        try:
            # Tokenize and normalize
            words = explanation.lower().split()
            unique_words = set(words)

            if len(words) == 0:
                return 0.0

            # Stopwords list (keeping original set for backward compatibility)
            stopwords = {
                "the", "and", "or", "but", "a", "an", "is", "are", "was",
                "were", "in", "on", "at", "to", "for",
            }

            # Identify meaningful words with improved logic:
            # - Not a stopword
            # - Either length > 2 OR is a recognized technical term
            meaningful_words = []
            technical_term_count = 0

            for w in unique_words:
                if w in stopwords:
                    continue

                # Check if it's a technical term (bypass length requirement)
                if w in self.TECHNICAL_TERMS:
                    meaningful_words.append(w)
                    technical_term_count += 1
                elif len(w) > 2:
                    meaningful_words.append(w)

            meaningful_count = len(meaningful_words)
            word_count = len(words)

            # Apply minimum score floor for any non-empty explanation
            if meaningful_count == 0:
                return self.MINIMUM_EXPLANATION_SCORE

            # Handle short explanations with special logic
            # Short non-technical explanations score low (original behavior)
            # Short technical explanations get a boost (new behavior)
            if meaningful_count <= 2:
                if technical_term_count > 0:
                    # Technical terms present: give reasonable score
                    # Base of 0.15 + 0.05 per technical term, capped at 0.25
                    return min(0.15 + technical_term_count * 0.05, 0.25)
                else:
                    # No technical terms: keep original low score behavior
                    return self.MINIMUM_EXPLANATION_SCORE

            # For longer explanations: calculate full score
            # Uniqueness ratio (meaningful unique words vs total words)
            uniqueness_ratio = meaningful_count / max(word_count, 1)

            # Length score (normalize to 20 meaningful words as target)
            length_score = min(meaningful_count / 20.0, 1.0)

            # Technical term bonus: boost score if explanation contains
            # recognized technical vocabulary (indicates domain expertise)
            technical_bonus = min(technical_term_count * 0.05, 0.15)

            # Combine metrics with technical term bonus
            base_score = 0.5 * uniqueness_ratio + 0.5 * length_score
            quality_score = base_score + technical_bonus

            return min(max(quality_score, self.MINIMUM_EXPLANATION_SCORE), 1.0)

        except Exception as e:
            logger.error(f"Explanation quality calculation error: {e}")
            return self.MINIMUM_EXPLANATION_SCORE  # Return floor instead of 0 on error

    async def calculate_understanding_score(self, concept_id: str) -> Success | Error:
        """
        Calculate overall understanding score (0.0-1.0).

        Combines three components with weights:
            - 40% relationship density
            - 30% explanation quality
            - 30% metadata completeness
        """
        try:
            # Get concept data
            concept_result = await self.data_access.get_concept_for_confidence(concept_id)
            if isinstance(concept_result, Error):
                return concept_result

            concept_data = concept_result.value

            # Calculate relationship density
            density_result = await self.calculate_relationship_density(concept_id)
            if isinstance(density_result, Error):
                return density_result
            density_score = density_result.value

            # Calculate explanation quality
            explanation_score = self.calculate_explanation_quality(concept_data.explanation)

            # Calculate metadata completeness
            completeness_report = check_data_completeness(concept_data)
            metadata_score = completeness_report.metadata_score

            # Weighted combination
            understanding_score = (
                self.RELATIONSHIP_WEIGHT * density_score
                + self.EXPLANATION_WEIGHT * explanation_score
                + self.METADATA_WEIGHT * metadata_score
            )

            # Ensure within bounds
            understanding_score = max(0.0, min(1.0, understanding_score))

            logger.info(
                f"Understanding score calculated for {concept_id}",
                extra={
                    "density": density_score,
                    "explanation": explanation_score,
                    "metadata": metadata_score,
                    "final": understanding_score,
                },
            )

            return Success(understanding_score)

        except Exception as e:
            logger.error(f"Understanding score calculation error: {e}")
            return Error(
                f"Failed to calculate understanding score: {e!s}",
                ErrorCode.DATABASE_ERROR,
            )
