"""
Token Efficiency Analysis for MCP Tools

This script measures token usage across all MCP tools to ensure
efficient responses that minimize token consumption while maintaining
functionality and clarity.

Usage:
    python tests/token_analysis.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


try:
    import tiktoken
except ImportError:
    print("❌ Error: tiktoken not installed. Install with: pip install tiktoken")
    sys.exit(1)


class TokenAnalyzer:
    """
    Analyzes token efficiency of MCP tool responses.

    Uses tiktoken with cl100k_base encoding (GPT-4/Claude compatible)
    to count tokens in JSON responses.
    """

    def __init__(self):
        """Initialize token analyzer with cl100k_base encoding."""
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.results = []

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Input text to count tokens

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def count_json_tokens(self, data: dict[str, Any]) -> int:
        """
        Count tokens in a JSON response (compact format).

        Args:
            data: JSON data dictionary

        Returns:
            Number of tokens in compact JSON representation
        """
        # Use compact JSON (no whitespace) for accurate token count
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return self.count_tokens(json_str)

    def analyze_tool(
        self, tool_name: str, mock_response: dict[str, Any], target_tokens: int, notes: str = ""
    ) -> dict[str, Any]:
        """
        Analyze a single tool's response.

        Args:
            tool_name: Name of the MCP tool
            mock_response: Mock response dictionary
            target_tokens: Target token count
            notes: Additional notes or context

        Returns:
            Analysis result dictionary
        """
        actual_tokens = self.count_json_tokens(mock_response)
        percentage = (actual_tokens / target_tokens * 100) if target_tokens > 0 else 0
        status = "✅ PASS" if actual_tokens <= target_tokens else "⚠️ OVER"

        result = {
            "tool_name": tool_name,
            "target_tokens": target_tokens,
            "actual_tokens": actual_tokens,
            "percentage": round(percentage, 1),
            "status": status,
            "over_by": max(0, actual_tokens - target_tokens),
            "notes": notes,
            "response": mock_response,
        }

        self.results.append(result)
        return result

    def generate_report(self) -> str:
        """
        Generate comprehensive token efficiency report.

        Returns:
            Markdown-formatted report
        """
        total_tools = len(self.results)
        passing_tools = sum(1 for r in self.results if "PASS" in r["status"])
        failing_tools = total_tools - passing_tools

        report = f"""# Token Efficiency Analysis Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Tools Analyzed**: {total_tools}
**Passing**: {passing_tools} ({passing_tools/total_tools*100:.1f}%)
**Over Target**: {failing_tools} ({failing_tools/total_tools*100:.1f}%)

---

## Executive Summary

"""

        if failing_tools == 0:
            report += "✅ **ALL TOOLS MEET TOKEN EFFICIENCY TARGETS**\n\n"
            report += "All MCP tools are producing responses within their target token budgets. "
            report += "No optimizations required at this time.\n\n"
        else:
            report += f"⚠️ **{failing_tools} TOOL(S) EXCEED TOKEN TARGETS**\n\n"
            report += (
                "The following tools require optimization to meet token efficiency targets:\n\n"
            )
            for r in self.results:
                if "OVER" in r["status"]:
                    report += f"- **{r['tool_name']}**: {r['actual_tokens']} tokens "
                    report += f"({r['percentage']}% of target, over by {r['over_by']})\n"
            report += "\n"

        report += "---\n\n"
        report += "## Detailed Results\n\n"
        report += "| Tool | Target | Actual | % of Target | Status | Over By |\n"
        report += "|------|--------|--------|-------------|--------|----------|\n"

        for r in sorted(self.results, key=lambda x: x["percentage"], reverse=True):
            report += f"| {r['tool_name']} | {r['target_tokens']} | {r['actual_tokens']} | "
            report += f"{r['percentage']}% | {r['status']} | {r['over_by']} |\n"

        report += "\n---\n\n"
        report += "## Tool-by-Tool Analysis\n\n"

        for r in self.results:
            report += f"### {r['tool_name']}\n\n"
            report += f"**Target**: {r['target_tokens']} tokens | "
            report += f"**Actual**: {r['actual_tokens']} tokens | "
            report += f"**Status**: {r['status']}\n\n"

            if r["notes"]:
                report += f"**Notes**: {r['notes']}\n\n"

            # Token breakdown
            json.dumps(r["response"], separators=(",", ":"), ensure_ascii=False)
            report += "**Response Structure**:\n```json\n"
            report += json.dumps(r["response"], indent=2)
            report += "\n```\n\n"

            # Field analysis
            if isinstance(r["response"], dict):
                report += "**Field Token Breakdown**:\n"
                for key, value in r["response"].items():
                    field_str = json.dumps({key: value}, separators=(",", ":"))
                    field_tokens = self.count_tokens(field_str)
                    report += f"- `{key}`: {field_tokens} tokens\n"
                report += "\n"

            # Recommendations
            if "OVER" in r["status"]:
                report += "**Optimization Recommendations**:\n"
                report += self._generate_recommendations(r)
                report += "\n"

            report += "---\n\n"

        # Summary recommendations
        if failing_tools > 0:
            report += "## Overall Recommendations\n\n"
            report += (
                "1. **Review field necessity**: Remove optional fields that add minimal value\n"
            )
            report += "2. **Implement pagination**: For tools with large result sets\n"
            report += "3. **Truncate text fields**: Limit explanation/notes to essential content\n"
            report += "4. **Use compact formats**: Remove unnecessary nesting and structure\n"
            report += "5. **Cache responses**: Implement client-side caching where appropriate\n\n"

        report += "---\n\n"
        report += "## Token Counting Methodology\n\n"
        report += "- **Encoding**: cl100k_base (GPT-4/Claude compatible)\n"
        report += "- **Format**: Compact JSON (no whitespace)\n"
        report += "- **Library**: tiktoken v0.5.1+\n"
        report += "- **Response Type**: Complete tool responses including all fields\n\n"

        return report

    def _generate_recommendations(self, result: dict[str, Any]) -> str:
        """Generate optimization recommendations for a tool."""
        recs = ""
        over_by = result["over_by"]

        if over_by < 50:
            recs += "- **Minor optimization needed**: Consider removing 1-2 optional fields\n"
        elif over_by < 150:
            recs += (
                "- **Moderate optimization needed**: Remove non-essential fields or truncate text\n"
            )
        else:
            recs += "- **Significant optimization needed**: Major restructuring required\n"

        # Check for arrays
        response = result["response"]
        if isinstance(response, dict):
            for key, value in response.items():
                if isinstance(value, list) and len(value) > 10:
                    recs += (
                        f"- Implement pagination for `{key}` array (currently {len(value)} items)\n"
                    )
                elif isinstance(value, str) and len(value) > 200:
                    recs += f"- Truncate `{key}` field (currently {len(value)} chars)\n"

        return recs

    def save_results(self, output_path: Path):
        """Save analysis results to JSON file."""
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "total_tools": len(self.results),
            "passing": sum(1 for r in self.results if "PASS" in r["status"]),
            "results": self.results,
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)


def create_mock_responses() -> list[tuple[str, dict[str, Any], int, str]]:
    """
    Create realistic mock responses for all 16 MCP tools.

    Returns:
        List of tuples: (tool_name, mock_response, target_tokens, notes)
    """
    return [
        # Concept CRUD Tools
        (
            "create_concept",
            {"success": True, "concept_id": "concept-abc123def456", "message": "Concept created"},
            50,
            "Minimal response for concept creation",
        ),
        (
            "get_concept",
            {
                "success": True,
                "concept": {
                    "concept_id": "concept-abc123def456",
                    "name": "Python For Loop",
                    "explanation": "A for loop iterates over a sequence of elements, executing a block of code for each element. Syntax: for item in sequence: <code block>",
                    "area": "Programming",
                    "topic": "Python",
                    "subtopic": "Control Flow",
                    "confidence_score": 95.0,
                    "created_at": "2025-10-07T10:00:00",
                    "last_modified": "2025-10-07T10:30:00",
                },
                "message": "Concept retrieved",
            },
            300,
            "Full concept data without history",
        ),
        (
            "update_concept",
            {
                "success": True,
                "updated_fields": ["explanation", "confidence_score"],
                "message": "Concept updated"
            },
            50,
            "Minimal response listing updated fields",
        ),
        (
            "delete_concept",
            {"success": True, "concept_id": "concept-abc123def456", "message": "Concept deleted"},
            30,
            "Minimal response for deletion",
        ),
        # Search Tools
        (
            "search_concepts_semantic",
            {
                "success": True,
                "results": [
                    {
                        "concept_id": f"concept-{i:03d}",
                        "name": f"Example Concept {i}",
                        "similarity": 0.95 - (i * 0.05),
                        "area": "Programming",
                        "topic": "Python",
                        "confidence_score": 90.0
                    }
                    for i in range(10)
                ],
                "total": 10,
                "message": "Found 10 concepts",
            },
            200,
            "10 search results with 6 fields each",
        ),
        (
            "search_concepts_exact",
            {
                "success": True,
                "results": [
                    {
                        "concept_id": f"concept-{i:03d}",
                        "name": f"Example Concept {i}",
                        "area": "Programming",
                        "topic": "Python",
                        "subtopic": "Control Flow",
                        "confidence_score": 90.0,
                        "created_at": "2025-10-07T10:00:00"
                    }
                    for i in range(10)
                ],
                "total": 10,
                "message": "Found 10 concepts",
            },
            200,
            "10 search results with 7 fields each",
        ),
        (
            "get_recent_concepts",
            {
                "success": True,
                "results": [
                    {
                        "concept_id": f"concept-{i:03d}",
                        "name": f"Recent Concept {i}",
                        "area": "Programming",
                        "topic": "Python",
                        "subtopic": "Control Flow",
                        "confidence_score": 90.0,
                        "created_at": "2025-10-07T10:00:00",
                        "last_modified": "2025-10-07T10:30:00",
                    }
                    for i in range(10)
                ],
                "total": 10,
                "message": "Found 10 concepts from last 7 days",
            },
            200,
            "10 recent concepts with 8 fields each (known to exceed target)",
        ),
        # Relationship Tools
        (
            "create_relationship",
            {
                "success": True,
                "relationship_id": "rel-xyz789abc123",
                "message": "Relationship created",
            },
            30,
            "Minimal response for relationship creation",
        ),
        (
            "delete_relationship",
            {"success": True, "message": "Relationship deleted"},
            25,
            "Minimal response for relationship deletion",
        ),
        (
            "get_related_concepts",
            {
                "concept_id": "concept-abc123",
                "related": [
                    {
                        "concept_id": f"concept-rel-{i:03d}",
                        "name": f"Related Concept {i}",
                        "relationship_type": "relates_to",
                        "strength": 1.0,
                        "distance": 1,
                    }
                    for i in range(10)
                ],
                "total": 10,
            },
            200,
            "10 related concepts with relationship metadata",
        ),
        (
            "get_prerequisites",
            {
                "concept_id": "concept-abc123",
                "chain": [
                    {
                        "concept_id": f"concept-pre-{i:03d}",
                        "name": f"Prerequisite {i}",
                        "depth": i + 1,
                    }
                    for i in range(5)
                ],
                "total": 5,
            },
            150,
            "Prerequisite chain with depth information",
        ),
        (
            "get_concept_chain",
            {
                "success": True,
                "path": [
                    {"concept_id": "concept-001", "name": "Start Concept"},
                    {"concept_id": "concept-002", "name": "Middle Concept"},
                    {"concept_id": "concept-003", "name": "End Concept"},
                ],
                "length": 3,
            },
            80,
            "Shortest path between two concepts",
        ),
        # Analytics Tools
        (
            "list_hierarchy",
            {
                "success": True,
                "areas": [
                    {
                        "name": "Programming",
                        "concept_count": 25,
                        "topics": [
                            {
                                "name": "Python",
                                "concept_count": 15,
                                "subtopics": [
                                    {"name": "Control Flow", "concept_count": 5},
                                    {"name": "Data Structures", "concept_count": 10},
                                ],
                            }
                        ],
                    }
                ],
                "total_concepts": 25,
                "message": "Hierarchy retrieved",
            },
            300,
            "Complete hierarchy with nested structure (cached for 5 min)",
        ),
        (
            "get_concepts_by_confidence",
            {
                "success": True,
                "results": [
                    {
                        "concept_id": f"concept-cert-{i:03d}",
                        "name": f"Concept {i}",
                        "confidence_score": 50.0 + i,
                        "area": "Programming",
                        "topic": "Python",
                        "subtopic": "Control Flow",
                        "created_at": "2025-10-07T10:00:00",
                    }
                    for i in range(10)
                ],
                "total": 10,
                "message": "Found 10 concepts",
            },
            200,
            "10 concepts filtered by confidence range"
        ),
        # Auxiliary Tools
        (
            "ping",
            {
                "status": "ok",
                "message": "MCP Knowledge Server is running",
                "server_name": "mcp-knowledge-server",
                "timestamp": "2025-10-07T10:00:00",
            },
            50,
            "Server health check response",
        ),
        (
            "get_server_stats",
            {
                "event_store": {"total_events": 1234, "concept_events": 567},
                "outbox": {"pending": 5, "processed": 1229, "failed": 0},
                "status": "healthy",
            },
            80,
            "Server statistics and metrics",
        ),
    ]


def main():
    """Main entry point for token analysis."""
    print("🔍 MCP Token Efficiency Analysis")
    print("=" * 60)
    print()

    # Initialize analyzer
    analyzer = TokenAnalyzer()

    # Get mock responses
    mock_data = create_mock_responses()

    print(f"Analyzing {len(mock_data)} MCP tools...\n")

    # Analyze each tool
    for tool_name, mock_response, target_tokens, notes in mock_data:
        result = analyzer.analyze_tool(tool_name, mock_response, target_tokens, notes)
        print(
            f"{result['status']} {tool_name}: {result['actual_tokens']}/{result['target_tokens']} tokens"
        )

    print()
    print("=" * 60)

    # Summary
    passing = sum(1 for r in analyzer.results if "PASS" in r["status"])
    total = len(analyzer.results)
    print(f"✅ Passing: {passing}/{total} ({passing/total*100:.1f}%)")
    print(f"⚠️  Over Target: {total-passing}/{total} ({(total-passing)/total*100:.1f}%)")
    print()

    # Generate report
    print("📝 Generating detailed report...")
    report = analyzer.generate_report()

    # Save report
    report_path = Path(__file__).parent.parent / "docs" / "token_efficiency_report.md"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, "w") as f:
        f.write(report)

    print(f"✅ Report saved to: {report_path}")
    print()

    # Save raw results
    results_path = Path(__file__).parent / "token_analysis_results.json"
    analyzer.save_results(results_path)
    print(f"✅ Raw results saved to: {results_path}")
    print()

    print("🎉 Token efficiency analysis complete!")

    # Exit with appropriate code
    if passing < total:
        print(f"\n⚠️  Warning: {total-passing} tool(s) exceed token targets")
        return 1
    else:
        print("\n✅ All tools meet token efficiency targets!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
