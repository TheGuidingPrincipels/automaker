"""LLM tier classification for complex or low-confidence cases."""

from __future__ import annotations

import json
import logging
import time
import asyncio
from typing import TYPE_CHECKING

from src.taxonomy.schema import CategoryProposal, ClassificationResult

if TYPE_CHECKING:
    from src.sdk.client import ClaudeSDKClient
    from src.taxonomy.manager import TaxonomyManager

logger = logging.getLogger(__name__)


class LLMTierClassifier:
    """LLM-based classification for complex categorization decisions.

    Used as fallback when fast tier confidence is below threshold,
    or when new category proposals may be needed.
    """

    # Classification prompt template
    CLASSIFICATION_PROMPT = """You are a content classification expert. Classify the following content into the most appropriate taxonomy category.

Available taxonomy categories:
{taxonomy_tree}

Content to classify:
Title: {title}
Content (excerpt): {content_excerpt}

Instructions:
1. Analyze the content and determine the best matching category path
2. Provide your confidence (0.0-1.0) in the classification
3. List 2-3 alternative category paths if applicable
4. If no existing category fits well (confidence < 0.7), you may propose a new Level 3+ subcategory

Respond in JSON format:
{{
    "primary_path": "path/to/category",
    "confidence": 0.85,
    "alternatives": [
        {{"path": "alternative/path", "confidence": 0.6}},
        ...
    ],
    "reasoning": "Brief explanation",
    "new_category_proposal": null OR {{
        "name": "category_name",
        "description": "Description of the new category",
        "parent_path": "path/to/parent",
        "confidence": 0.9
    }}
}}"""

    def __init__(
        self,
        taxonomy_manager: TaxonomyManager,
        sdk_client: ClaudeSDKClient | None = None,
    ):
        """Initialize LLM tier classifier.

        Args:
            taxonomy_manager: Manager for taxonomy operations.
            sdk_client: Claude SDK client for LLM calls. If None, will be initialized on first use.
        """
        self.taxonomy_manager = taxonomy_manager
        self._sdk_client = sdk_client

    @property
    def sdk_client(self) -> ClaudeSDKClient:
        """Lazy load SDK client."""
        if self._sdk_client is None:
            from src.sdk.client import ClaudeSDKClient
            self._sdk_client = ClaudeSDKClient()
        return self._sdk_client

    def classify(
        self,
        title: str,
        content: str,
        max_content_length: int = 2000,
    ) -> ClassificationResult:
        """Classify content using LLM.

        Args:
            title: Content title.
            content: Full content text.
            max_content_length: Maximum content excerpt length.

        Returns:
            ClassificationResult with classification and potential new category proposal.
        """
        start_time = time.perf_counter()

        # Build taxonomy tree for prompt
        taxonomy_tree = self._build_taxonomy_tree()

        # Truncate content for prompt
        content_excerpt = content[:max_content_length]
        if len(content) > max_content_length:
            content_excerpt += "..."

        # Build and send prompt
        prompt = self.CLASSIFICATION_PROMPT.format(
            taxonomy_tree=taxonomy_tree,
            title=title,
            content_excerpt=content_excerpt,
        )

        try:
            response = self.sdk_client.complete(prompt)
            result = self._parse_response(response)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("LLM classification failed: %s", e)
            # Fallback to uncategorized
            result = ClassificationResult(
                primary_path="uncategorized",
                primary_confidence=0.0,
                alternatives=[],
                tier_used="llm",
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )
            return result
        except Exception as e:
            logger.exception("Unexpected error in LLM classification")
            raise

        result.processing_time_ms = (time.perf_counter() - start_time) * 1000
        result.tier_used = "llm"

        logger.debug(
            "LLM tier classified to %s (confidence: %.3f) in %.2fms",
            result.primary_path,
            result.primary_confidence,
            result.processing_time_ms,
        )

        return result

    async def classify_async(
        self,
        title: str,
        content: str,
        max_content_length: int = 2000,
    ) -> ClassificationResult:
        """Classify content using LLM (async).

        Args:
            title: Content title.
            content: Full content text.
            max_content_length: Maximum content excerpt length.

        Returns:
            ClassificationResult with classification and potential new category proposal.
        """
        start_time = time.perf_counter()

        taxonomy_tree = self._build_taxonomy_tree()

        content_excerpt = content[:max_content_length]
        if len(content) > max_content_length:
            content_excerpt += "..."

        prompt = self.CLASSIFICATION_PROMPT.format(
            taxonomy_tree=taxonomy_tree,
            title=title,
            content_excerpt=content_excerpt,
        )

        try:
            if hasattr(self.sdk_client, "complete_async"):
                response = await self.sdk_client.complete_async(prompt)
            else:
                response = await asyncio.to_thread(self.sdk_client.complete, prompt)
            result = self._parse_response(response)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("LLM classification failed: %s", e)
            result = ClassificationResult(
                primary_path="uncategorized",
                primary_confidence=0.0,
                alternatives=[],
                tier_used="llm",
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )
            return result
        except Exception:
            logger.exception("Unexpected error in LLM classification")
            raise

        result.processing_time_ms = (time.perf_counter() - start_time) * 1000
        result.tier_used = "llm"

        logger.debug(
            "LLM tier classified to %s (confidence: %.3f) in %.2fms",
            result.primary_path,
            result.primary_confidence,
            result.processing_time_ms,
        )

        return result

    def _build_taxonomy_tree(self) -> str:
        """Build a text representation of the taxonomy tree for the prompt.

        Returns:
            Formatted string showing taxonomy hierarchy.
        """
        if self.taxonomy_manager.config is None:
            return "No taxonomy loaded"

        lines = []
        for path in self.taxonomy_manager.get_all_paths():
            depth = path.count("/")
            indent = "  " * depth
            name = path.split("/")[-1]
            category = self.taxonomy_manager.get_category(path)
            description = category.description if category else ""
            lines.append(f"{indent}- {path}: {description}")

        return "\n".join(lines)

    def _parse_response(self, response: str) -> ClassificationResult:
        """Parse LLM response into ClassificationResult.

        Args:
            response: Raw LLM response text.

        Returns:
            Parsed ClassificationResult.

        Raises:
            ValueError: If response cannot be parsed.
        """
        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Try to find JSON object directly
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]

            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse LLM response as JSON: %s", e)
            raise ValueError(f"Invalid LLM response format: {e}")

        # Extract fields
        primary_path = data.get("primary_path", "uncategorized")
        primary_confidence = float(data.get("confidence", 0.0))

        # Parse alternatives
        alternatives = []
        for alt in data.get("alternatives", []):
            alt_path = alt.get("path", "")
            alt_conf = float(alt.get("confidence", 0.0))
            if alt_path:
                alternatives.append((alt_path, alt_conf))

        # Parse new category proposal
        new_category_proposal = None
        proposal_data = data.get("new_category_proposal")
        if proposal_data:
            new_category_proposal = CategoryProposal(
                name=proposal_data.get("name", ""),
                description=proposal_data.get("description", ""),
                parent_path=proposal_data.get("parent_path", ""),
                confidence=float(proposal_data.get("confidence", 0.0)),
            )

        return ClassificationResult(
            primary_path=primary_path,
            primary_confidence=primary_confidence,
            alternatives=alternatives,
            tier_used="llm",
            new_category_proposed=new_category_proposal,
            processing_time_ms=0.0,  # Will be set by caller
        )

    def validate_classification(
        self,
        path: str,
        title: str,
        content_excerpt: str,
    ) -> tuple[bool, str]:
        """Validate a classification decision using LLM.

        Args:
            path: Proposed classification path.
            title: Content title.
            content_excerpt: Content excerpt.

        Returns:
            Tuple of (is_valid, reason).
        """
        prompt = f"""Validate if the following content classification is appropriate.

Classification: {path}
Title: {title}
Content: {content_excerpt}

Is this classification appropriate? Respond with:
{{"valid": true/false, "reason": "brief explanation"}}"""

        try:
            response = self.sdk_client.complete(prompt)
            data = json.loads(response)
            valid = data.get("valid")
            if not isinstance(valid, bool):
                logger.warning("Invalid response format: 'valid' is not boolean")
                return True, "Validation skipped due to invalid response format"
            return valid, data.get("reason", "")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Classification validation failed: %s", e)
            return True, "Validation skipped due to error"
        except Exception as e:
            logger.exception("Unexpected error in classification validation")
            raise
