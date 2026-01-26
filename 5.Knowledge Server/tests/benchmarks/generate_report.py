"""
Performance report generator for MCP Knowledge Management Server.

Parses benchmark results and generates PERFORMANCE_REPORT.md with
tables, charts, and optimization recommendations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceReportGenerator:
    """Generates comprehensive performance reports from benchmark data"""

    def __init__(self):
        self.tool_results = {}
        self.concurrent_results = {}
        self.performance_targets = {
            "create_concept": 50,
            "get_concept": 50,
            "update_concept": 50,
            "delete_concept": 50,
            "search_concepts_semantic": 100,
            "search_concepts_exact": 100,
            "get_recent_concepts": 100,
            "create_relationship": 50,
            "delete_relationship": 50,
            "get_related_concepts": 200,
            "get_prerequisites": 200,
            "get_concept_chain": 200,
            "list_hierarchy": 300,
            "get_concepts_by_confidence": 100
        }

    def load_results(self, tool_results_file: str, concurrent_results_file: str):
        """Load benchmark results from JSON files"""
        logger.info("Loading benchmark results...")

        # Load tool benchmarks
        tool_path = Path(__file__).parent / tool_results_file
        if tool_path.exists():
            with open(tool_path) as f:
                self.tool_results = json.load(f)
            logger.info(f"✅ Loaded {len(self.tool_results)} tool results")
        else:
            logger.warning(f"Tool results file not found: {tool_path}")

        # Load concurrent benchmarks
        concurrent_path = Path(__file__).parent / concurrent_results_file
        if concurrent_path.exists():
            with open(concurrent_path) as f:
                self.concurrent_results = json.load(f)
            logger.info(f"✅ Loaded {len(self.concurrent_results)} concurrent results")
        else:
            logger.warning(f"Concurrent results file not found: {concurrent_path}")

    def generate_ascii_chart(self, value: float, max_value: float, width: int = 40) -> str:
        """Generate simple ASCII bar chart"""
        if max_value == 0:
            return ""

        filled = int((value / max_value) * width)
        bar = "█" * filled + "░" * (width - filled)
        return bar

    def get_status_indicator(self, actual: float, target: float) -> str:
        """Get status indicator based on performance vs target"""
        if actual <= target:
            return "✅ EXCELLENT"
        elif actual <= target * 1.5:
            return "✔️ GOOD"
        elif actual <= target * 2:
            return "⚠️ ACCEPTABLE"
        else:
            return "❌ NEEDS OPTIMIZATION"

    def generate_executive_summary(self) -> str:
        """Generate executive summary section"""
        total_tools = len(self.tool_results)
        excellent = sum(
            1
            for tool, data in self.tool_results.items()
            if data.get("p95_ms", float("inf")) <= self.performance_targets.get(tool, float("inf"))
        )
        needs_optimization = sum(
            1
            for tool, data in self.tool_results.items()
            if data.get("p95_ms", 0) > self.performance_targets.get(tool, 0) * 2
        )

        summary = f"""# Performance Benchmark Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**MCP Knowledge Management Server** - Version 1.0

## 📊 Executive Summary

- **Tools Benchmarked**: {total_tools}/14
- **Meeting Performance Targets**: {excellent}/{total_tools} ({excellent/total_tools*100:.1f}%)
- **Needing Optimization**: {needs_optimization}/{total_tools}
- **Concurrency Tests**: {len(self.concurrent_results)} scenarios

### Key Findings

"""

        # Find fastest and slowest tools
        sorted_tools = sorted(self.tool_results.items(), key=lambda x: x[1].get("p95_ms", 0))

        if sorted_tools:
            fastest = sorted_tools[0]
            slowest = sorted_tools[-1]

            summary += (
                f"- **Fastest Tool**: `{fastest[0]}` - {fastest[1].get('p95_ms', 0):.2f}ms P95\n"
            )
            summary += (
                f"- **Slowest Tool**: `{slowest[0]}` - {slowest[1].get('p95_ms', 0):.2f}ms P95\n"
            )

        # Concurrency findings
        if self.concurrent_results:
            # Find best throughput
            best_throughput = max(
                self.concurrent_results.values(), key=lambda x: x.get("throughput_ops_per_sec", 0)
            )
            summary += f"- **Best Throughput**: {best_throughput.get('throughput_ops_per_sec', 0):.2f} ops/sec "
            summary += f"({best_throughput.get('test', 'unknown')} @ {best_throughput.get('parallel_count', 0)}x)\n"

        summary += "\n---\n\n"
        return summary

    def generate_tool_performance_table(self) -> str:
        """Generate tool-by-tool performance breakdown"""
        section = "## 🔧 Individual Tool Performance\n\n"

        section += "| Tool | Iterations | P50 (ms) | P95 (ms) | P99 (ms) | Target | Status |\n"
        section += "|------|------------|----------|----------|----------|--------|--------|\n"

        for tool_name in sorted(self.tool_results.keys()):
            data = self.tool_results[tool_name]
            target = self.performance_targets.get(tool_name, 0)

            p50 = data.get("median_ms", 0)
            p95 = data.get("p95_ms", 0)
            p99 = data.get("p99_ms", 0)
            iterations = data.get("iterations", 0)

            status = self.get_status_indicator(p95, target)

            section += f"| `{tool_name}` | {iterations} | {p50:.2f} | {p95:.2f} | {p99:.2f} | {target} | {status} |\n"

        section += "\n### Performance Visualization\n\n"

        # Add ASCII charts for P95 times
        max_p95 = max(data.get("p95_ms", 0) for data in self.tool_results.values())

        for tool_name in sorted(self.tool_results.keys()):
            data = self.tool_results[tool_name]
            p95 = data.get("p95_ms", 0)
            chart = self.generate_ascii_chart(p95, max_p95, width=40)
            section += f"**{tool_name}**: {chart} {p95:.2f}ms\n\n"

        section += "\n---\n\n"
        return section

    def generate_detailed_breakdown(self) -> str:
        """Generate detailed breakdown for each tool"""
        section = "## 📈 Detailed Performance Breakdown\n\n"

        for tool_name in sorted(self.tool_results.keys()):
            data = self.tool_results[tool_name]
            target = self.performance_targets.get(tool_name, 0)

            section += f"### {tool_name}\n\n"
            section += "**Performance Metrics:**\n"
            section += f"- Iterations: {data.get('iterations', 0)}\n"
            section += f"- Min: {data.get('min_ms', 0):.2f}ms\n"
            section += f"- Mean: {data.get('mean_ms', 0):.2f}ms\n"
            section += f"- Median (P50): {data.get('median_ms', 0):.2f}ms\n"
            section += f"- P95: {data.get('p95_ms', 0):.2f}ms\n"
            section += f"- P99: {data.get('p99_ms', 0):.2f}ms\n"
            section += f"- Max: {data.get('max_ms', 0):.2f}ms\n"
            section += f"- Target: {target}ms\n\n"

            # Comparison to target
            p95 = data.get("p95_ms", 0)
            if p95 <= target:
                section += f"✅ **Status**: Exceeds performance target by {((target - p95) / target * 100):.1f}%\n\n"
            elif p95 <= target * 2:
                section += f"⚠️ **Status**: Within acceptable range ({((p95 - target) / target * 100):.1f}% over target)\n\n"
            else:
                section += f"❌ **Status**: Needs optimization ({((p95 - target) / target * 100):.1f}% over target)\n\n"

        section += "---\n\n"
        return section

    def generate_concurrency_results(self) -> str:
        """Generate concurrency test results"""
        section = "## 🚀 Concurrency Test Results\n\n"

        section += "### Throughput by Parallelism Level\n\n"
        section += "| Test Type | Parallelism | Operations | Success Rate | Throughput (ops/sec) | Avg Latency (ms) |\n"
        section += "|-----------|-------------|------------|--------------|---------------------|------------------|\n"

        for test_name in sorted(self.concurrent_results.keys()):
            data = self.concurrent_results[test_name]

            success_rate = (data.get("successful", 0) / data.get("total_operations", 1)) * 100
            section += f"| {data.get('test', 'unknown')} | {data.get('parallel_count', 0)}x | "
            section += f"{data.get('total_operations', 0)} | {success_rate:.1f}% | "
            section += f"{data.get('throughput_ops_per_sec', 0):.2f} | "
            section += f"{data.get('avg_latency_ms', 0):.2f} |\n"

        section += "\n### Analysis\n\n"

        # Group by test type
        test_types = {}
        for test_name, data in self.concurrent_results.items():
            test_type = data.get("test", "unknown")
            if test_type not in test_types:
                test_types[test_type] = []
            test_types[test_type].append(data)

        for test_type, results in test_types.items():
            section += f"**{test_type}:**\n"

            throughputs = [r.get("throughput_ops_per_sec", 0) for r in results]
            if throughputs:
                section += f"- Best throughput: {max(throughputs):.2f} ops/sec\n"
                section += f"- Lowest throughput: {min(throughputs):.2f} ops/sec\n"

                # Check for degradation
                if len(throughputs) >= 2:
                    degradation = ((throughputs[0] - throughputs[-1]) / throughputs[0]) * 100
                    if degradation > 0:
                        section += (
                            f"- Throughput degradation: {degradation:.1f}% (5x → 20x parallelism)\n"
                        )

            section += "\n"

        section += "---\n\n"
        return section

    def generate_recommendations(self) -> str:
        """Generate optimization recommendations"""
        section = "## 💡 Optimization Recommendations\n\n"

        # Find tools needing optimization
        needs_opt = []
        for tool_name, data in self.tool_results.items():
            target = self.performance_targets.get(tool_name, 0)
            p95 = data.get("p95_ms", 0)

            if p95 > target * 2:
                over_target_pct = ((p95 - target) / target) * 100
                needs_opt.append((tool_name, p95, target, over_target_pct))

        if needs_opt:
            section += "### High Priority Optimizations\n\n"
            section += "The following tools exceed performance targets by >100%:\n\n"

            for tool_name, p95, target, over_pct in sorted(
                needs_opt, key=lambda x: x[3], reverse=True
            ):
                section += f"#### {tool_name}\n"
                section += f"- Current P95: {p95:.2f}ms\n"
                section += f"- Target: {target}ms\n"
                section += f"- Over target by: {over_pct:.1f}%\n"
                section += "- **Recommendations**:\n"

                # Tool-specific recommendations
                if "search" in tool_name:
                    section += "  - Review database index coverage\n"
                    section += "  - Consider caching frequent queries\n"
                    section += "  - Optimize embedding generation pipeline\n"
                elif "create" in tool_name or "update" in tool_name:
                    section += "  - Review dual-write synchronization\n"
                    section += "  - Consider batch operations\n"
                    section += "  - Optimize event store writes\n"
                elif "hierarchy" in tool_name or "list" in tool_name:
                    section += "  - Extend cache TTL\n"
                    section += "  - Optimize aggregation queries\n"
                    section += "  - Consider materialized views\n"
                else:
                    section += "  - Profile execution to identify bottlenecks\n"
                    section += "  - Review database query performance\n"

                section += "\n"
        else:
            section += "✅ **No high-priority optimizations needed!** All tools are performing within acceptable ranges.\n\n"

        section += "### General Recommendations\n\n"
        section += "- Continue monitoring performance in production environments\n"
        section += "- Establish performance regression tests in CI/CD\n"
        section += "- Set up alerting for P95 latency thresholds\n"
        section += "- Consider horizontal scaling for high-throughput scenarios\n\n"

        section += "---\n\n"
        return section

    def generate_report(self, output_file: str = "PERFORMANCE_REPORT.md"):
        """Generate complete performance report"""
        logger.info("Generating performance report...")

        report = ""
        report += self.generate_executive_summary()
        report += self.generate_tool_performance_table()
        report += self.generate_detailed_breakdown()
        report += self.generate_concurrency_results()
        report += self.generate_recommendations()

        # Footer
        report += "## 📝 Notes\n\n"
        report += "- All measurements taken on local development environment\n"
        report += "- Results may vary in production based on hardware and load\n"
        report += "- Benchmarks include full dual-database writes and event sourcing\n"
        report += "- P95 target = 95% of requests complete within this time\n\n"
        report += (
            f"---\n\n*Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n"
        )

        # Save report
        output_path = Path(__file__).parent.parent.parent / output_file

        with open(output_path, "w") as f:
            f.write(report)

        logger.info(f"✅ Report saved to {output_path}")


def main():
    """Main entry point for report generation"""
    generator = PerformanceReportGenerator()

    try:
        generator.load_results("benchmark_results.json", "concurrent_results.json")
        generator.generate_report()

        print("\n" + "=" * 80)
        print("✅ PERFORMANCE REPORT GENERATED")
        print("=" * 80)
        print("\nReport location: PERFORMANCE_REPORT.md")
        print("\nOpen the report to view detailed performance analysis and recommendations.")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise


if __name__ == "__main__":
    main()
