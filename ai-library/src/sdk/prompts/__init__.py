"""System prompts for different modes of operation."""

from .cleanup_mode import CLEANUP_SYSTEM_PROMPT, build_cleanup_prompt
from .routing_mode import ROUTING_SYSTEM_PROMPT, build_routing_prompt
from .output_mode import OUTPUT_SYSTEM_PROMPT

__all__ = [
    "CLEANUP_SYSTEM_PROMPT",
    "build_cleanup_prompt",
    "ROUTING_SYSTEM_PROMPT",
    "build_routing_prompt",
    "OUTPUT_SYSTEM_PROMPT",
]
