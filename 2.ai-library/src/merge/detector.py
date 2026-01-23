# src/merge/detector.py
"""
Merge candidate detection for REFINEMENT mode.

Finds existing library content that could be merged with incoming blocks,
based on topic similarity and content overlap.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import anyio


@dataclass
class MergeCandidate:
    """A potential merge target in the library."""
    block_id: str                    # Source block ID
    target_file: str                 # Library file path
    target_section: Optional[str]    # Section title (if applicable)
    target_content: str              # Existing content to merge with
    similarity_score: float          # 0-1 similarity score
    overlap_phrases: List[str]       # Common phrases/concepts
    merge_reasoning: str             # Why this is a good merge candidate


class MergeDetector:
    """
    Detects potential merge candidates in the library.

    Only active in REFINEMENT mode. In STRICT mode, merge is forbidden.

    Uses text similarity and phrase overlap to find existing content
    that could be combined with incoming blocks.
    """

    COMMON_START_WORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'this', 'that',
        'it', 'to', 'for', 'in', 'on', 'with', 'as', 'by', 'from',
    }

    def __init__(
        self,
        library_path: str = "./library",
        similarity_threshold: float = 0.3,
        min_phrase_overlap: int = 2,
    ):
        """
        Initialize the merge detector.

        Args:
            library_path: Path to the library directory
            similarity_threshold: Minimum similarity score for candidates
            min_phrase_overlap: Minimum number of overlapping phrases
        """
        self.library_path = Path(library_path)
        self.similarity_threshold = similarity_threshold
        self.min_phrase_overlap = min_phrase_overlap

    def _extract_phrases(self, text: str, min_words: int = 2, max_words: int = 5) -> Set[str]:
        """
        Extract meaningful phrases from text.

        Args:
            text: Input text
            min_words: Minimum words per phrase
            max_words: Maximum words per phrase

        Returns:
            Set of normalized phrases
        """
        # Clean text
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]+`', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'[#*_~]', '', text)

        # Split into sentences
        sentences = re.split(r'[.!?\n]+', text)

        phrases = set()
        for sentence in sentences:
            words = sentence.lower().split()
            words = [w for w in words if re.match(r'^[a-z][a-z0-9-]*$', w)]

            # Extract n-grams
            for n in range(min_words, min(max_words + 1, len(words) + 1)):
                for i in range(len(words) - n + 1):
                    phrase = ' '.join(words[i:i + n])
                    # Filter common phrases
                    if not self._is_common_phrase(phrase):
                        phrases.add(phrase)

        return phrases

    def _is_common_phrase(self, phrase: str) -> bool:
        """Check if phrase is too common to be meaningful."""
        words = phrase.split()
        if words and words[0] in self.COMMON_START_WORDS:
            return True
        return len(phrase) < 5

    def _compute_similarity(
        self,
        source_phrases: Set[str],
        target_phrases: Set[str],
    ) -> tuple[float, List[str]]:
        """
        Compute phrase-based similarity between texts.

        Args:
            source_phrases: Phrases from source block
            target_phrases: Phrases from target content

        Returns:
            Tuple of (similarity score, list of overlapping phrases)
        """
        if not source_phrases or not target_phrases:
            return 0.0, []

        overlap = source_phrases & target_phrases
        overlap_list = sorted(overlap, key=len, reverse=True)

        # Jaccard-like similarity
        union = source_phrases | target_phrases
        similarity = len(overlap) / len(union) if union else 0.0

        return similarity, overlap_list

    async def _read_library_file(self, file_path: Path) -> Optional[str]:
        """Read content from a library file."""
        try:
            path = anyio.Path(file_path)
            if await path.exists():
                return await path.read_text()
        except Exception:
            pass
        return None

    async def _extract_sections(self, content: str) -> Dict[str, str]:
        """
        Extract sections from markdown content.

        Args:
            content: Markdown content

        Returns:
            Dictionary mapping section title to section content
        """
        sections = {}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            # Check for heading
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()

                current_section = heading_match.group(2).strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    async def find_merge_candidates(
        self,
        block: Dict[str, Any],
        library_context: Dict[str, Any],
        content_mode: str = "strict",
    ) -> List[MergeCandidate]:
        """
        Find potential merge candidates for a block.

        Args:
            block: Source block dictionary
            library_context: Library manifest context
            content_mode: "strict" or "refinement"

        Returns:
            List of MergeCandidate objects, sorted by similarity descending
        """
        # Merge only allowed in REFINEMENT mode
        if content_mode.lower() != "refinement":
            return []

        block_content = block.get("content", "")
        block_id = block.get("id", "unknown")
        block_phrases = self._extract_phrases(block_content)

        if not block_phrases:
            return []

        candidates = []

        # Flatten files from categories
        def flatten_files(categories: List[Dict]) -> List[Dict]:
            files = []
            for cat in categories:
                for f in cat.get("files", []):
                    f_with_path = dict(f)
                    f_with_path["full_path"] = str(self.library_path / f["path"])
                    files.append(f_with_path)
                files.extend(flatten_files(cat.get("subcategories", [])))
            return files

        all_files = flatten_files(library_context.get("categories", []))

        for file_info in all_files:
            file_path = Path(file_info.get("full_path", ""))
            rel_path = file_info.get("path", "")

            content = await self._read_library_file(file_path)
            if not content:
                continue

            # Check file-level similarity
            file_phrases = self._extract_phrases(content)
            file_sim, file_overlap = self._compute_similarity(block_phrases, file_phrases)

            if file_sim >= self.similarity_threshold and len(file_overlap) >= self.min_phrase_overlap:
                # Check section-level similarity for more precise targeting
                sections = await self._extract_sections(content)

                best_section = None
                best_section_sim = 0.0
                best_section_overlap: List[str] = []
                best_section_content = ""

                for section_title, section_content in sections.items():
                    section_phrases = self._extract_phrases(section_content)
                    sec_sim, sec_overlap = self._compute_similarity(
                        block_phrases, section_phrases
                    )

                    if sec_sim > best_section_sim:
                        best_section = section_title
                        best_section_sim = sec_sim
                        best_section_overlap = sec_overlap
                        best_section_content = section_content

                # Use section-level if better than file-level
                if best_section_sim > file_sim:
                    candidates.append(
                        MergeCandidate(
                            block_id=block_id,
                            target_file=rel_path,
                            target_section=best_section,
                            target_content=best_section_content[:500],
                            similarity_score=best_section_sim,
                            overlap_phrases=best_section_overlap[:5],
                            merge_reasoning=self._generate_reasoning(
                                best_section_overlap, best_section_sim
                            ),
                        )
                    )
                else:
                    candidates.append(
                        MergeCandidate(
                            block_id=block_id,
                            target_file=rel_path,
                            target_section=None,
                            target_content=content[:500],
                            similarity_score=file_sim,
                            overlap_phrases=file_overlap[:5],
                            merge_reasoning=self._generate_reasoning(
                                file_overlap, file_sim
                            ),
                        )
                    )

        # Sort by similarity score
        candidates.sort(key=lambda c: c.similarity_score, reverse=True)
        return candidates[:5]  # Top 5 candidates

    def _generate_reasoning(
        self,
        overlap_phrases: List[str],
        similarity: float,
    ) -> str:
        """Generate human-readable reasoning for merge suggestion."""
        if similarity > 0.5:
            strength = "strong"
        elif similarity > 0.3:
            strength = "moderate"
        else:
            strength = "weak"

        if overlap_phrases:
            phrases_str = ", ".join(f'"{p}"' for p in overlap_phrases[:3])
            return f"{strength.capitalize()} topic overlap ({similarity:.0%}). Shared concepts: {phrases_str}"
        else:
            return f"{strength.capitalize()} similarity ({similarity:.0%}) based on content analysis"
