"""System prompts for different modes of operation."""

from .cleanup_mode import (
    CLEANUP_SYSTEM_PROMPT,
    CLEANUP_SYSTEM_PROMPT_CONSERVATIVE,
    CLEANUP_SYSTEM_PROMPT_BALANCED,
    CLEANUP_SYSTEM_PROMPT_AGGRESSIVE,
    get_cleanup_system_prompt,
    build_cleanup_prompt,
)
from .routing_mode import ROUTING_SYSTEM_PROMPT, build_routing_prompt
from .output_mode import OUTPUT_SYSTEM_PROMPT, build_query_prompt

__all__ = [
    # Cleanup mode prompts and functions
    "CLEANUP_SYSTEM_PROMPT",
    "CLEANUP_SYSTEM_PROMPT_CONSERVATIVE",
    "CLEANUP_SYSTEM_PROMPT_BALANCED",
    "CLEANUP_SYSTEM_PROMPT_AGGRESSIVE",
    "get_cleanup_system_prompt",
    "build_cleanup_prompt",
    # Routing mode
    "ROUTING_SYSTEM_PROMPT",
    "build_routing_prompt",
    # Output mode
    "OUTPUT_SYSTEM_PROMPT",
    "build_query_prompt",
]
