#!/usr/bin/env python3
"""
Backend Test Executor - Direct Execution
Runs comprehensive backend tests and generates results.json
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


# Configuration
REPO_ROOT = Path(__file__).parent
OUTPUT_DIR = REPO_ROOT / ".test-output" / "intermediate"
PYTEST_BIN = REPO_ROOT / ".venv" / "bin" / "pytest"


def main():
    """Main execution function."""
    start_time = time.time()

    print("=" * 80)
    print("BACKEND TESTER - Comprehensive Test Execution")
    print("=" * 80)
    print(f"Repository: {REPO_ROOT}")
    print(f"Python: {sys.executable}")
    print(f"Pytest: {PYTEST_BIN}")
    print("Time budget: 8 minutes (480 seconds)")
    print("=" * 80)

    # Change to repo directory
    os.chdir(REPO_ROOT)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Define output files
    coverage_json = OUTPUT_DIR / "coverage.json"
    results_file = OUTPUT_DIR / "backend-results.json"

    # Build pytest command
    cmd = [
        str(PYTEST_BIN),
        "tests/",
        f"--cov={REPO_ROOT}",
        f"--cov-report=json:{coverage_json}",
        "--cov-report=term-missing:skip-covered",
        "-v",
        "--tb=short",
        "--color=yes",
    ]

    print(f"\nCommand: {' '.join(cmd)}\n")
    print("=" * 80)
    print("EXECUTING TESTS...\n")

    # Execute tests
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=420, cwd=REPO_ROOT  # 7 minutes
        )

        duration = time.time() - start_time

        print("=" * 80)
        print("TEST EXECUTION COMPLETE")
        print("=" * 80)
        print(f"Duration: {duration:.1f} seconds")
        print(f"Exit code: {result.returncode}")
        print("=" * 80)

        # Show output
        print("\n" + result.stdout)

        if result.stderr:
            print("\nSTDERR:\n" + result.stderr)

        # Parse results
        test_counts, failures = parse_pytest_output(result.stdout + "\n" + result.stderr)
        coverage_data = parse_coverage(coverage_json)

        # Determine status
        if result.returncode == 0:
            status = "success"
        elif test_counts["total"] > 0:
            status = "success"  # Tests ran, some may have failed
        else:
            status = "failed"  # Infrastructure failure

        # Build results
        results = {
            "agent_name": "backend-tester",
            "status": status,
            "duration_seconds": int(duration),
            "results": {
                "test_counts": test_counts,
                "coverage": coverage_data,
                "failures": failures,
            },
        }

        # Write results
        write_results(results, results_file)

        return 0 if status == "success" else 1

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"\nTIMEOUT after {duration:.1f} seconds - Writing partial results")

        results = {
            "agent_name": "backend-tester",
            "status": "timeout",
            "duration_seconds": int(duration),
            "results": {
                "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
                "coverage": {
                    "overall": 0.0,
                    "line_coverage": 0.0,
                    "branch_coverage": 0.0,
                    "by_module": {},
                    "by_file": {},
                },
                "failures": [],
            },
        }

        write_results(results, results_file)
        return 1

    except Exception as e:
        duration = time.time() - start_time
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()

        results = {
            "agent_name": "backend-tester",
            "status": "failed",
            "duration_seconds": int(duration),
            "results": {
                "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
                "coverage": {
                    "overall": 0.0,
                    "line_coverage": 0.0,
                    "branch_coverage": 0.0,
                    "by_module": {},
                    "by_file": {},
                },
                "failures": [
                    {
                        "test_id": "infrastructure_error",
                        "test_name": "Test execution infrastructure error",
                        "test_file": "N/A",
                        "test_line": 0,
                        "failure_type": "runtime_error",
                        "severity": "high",
                        "diagnostic_context": {
                            "expected": "Tests execute successfully",
                            "actual": str(e),
                            "stack_trace": traceback.format_exc()[:1500],
                            "root_cause_hint": "Infrastructure or framework error - check dependencies",
                            "fix_priority": 100,
                        },
                    }
                ],
            },
        }

        write_results(results, results_file)
        return 1


def parse_pytest_output(output):
    """Parse pytest output to extract test counts and failures."""
    test_counts = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
    failures = []

    # Parse summary line patterns
    # Examples: "10 passed in 5.23s", "5 passed, 2 failed, 1 skipped in 10s"
    passed_match = re.search(r"(\d+)\s+passed", output)
    failed_match = re.search(r"(\d+)\s+failed", output)
    skipped_match = re.search(r"(\d+)\s+skipped", output)

    if passed_match:
        test_counts["passed"] = int(passed_match.group(1))
    if failed_match:
        test_counts["failed"] = int(failed_match.group(1))
    if skipped_match:
        test_counts["skipped"] = int(skipped_match.group(1))

    test_counts["total"] = test_counts["passed"] + test_counts["failed"] + test_counts["skipped"]

    # Parse individual failures
    # Look for "FAILED test_file.py::TestClass::test_method - Error: message"
    failure_pattern = r"FAILED\s+([^\s]+)\s+-\s+(.+?)(?=\nFAILED|\n=|$)"

    for match in re.finditer(failure_pattern, output, re.DOTALL):
        test_path = match.group(1)
        error_msg = match.group(2).strip()

        # Parse test components
        parts = test_path.split("::")
        test_file = parts[0] if parts else "unknown"
        test_name = parts[-1] if len(parts) > 1 else "unknown"

        # Determine failure type
        failure_type = "assertion_error"
        if "timeout" in error_msg.lower():
            failure_type = "timeout"
        elif (
            "error" in error_msg.lower() or "exception" in error_msg.lower()
        ) and "assertion" not in error_msg.lower():
            failure_type = "runtime_error"

        # Determine severity
        severity = "medium"
        if "e2e" in test_file or "integration" in test_file or "failures" in test_file:
            severity = "high"

        # Calculate fix priority
        priority = 50
        if severity == "high":
            priority += 30
        if "e2e" in test_file:
            priority += 15
        elif "integration" in test_file:
            priority += 10
        if failure_type == "timeout":
            priority += 5
        elif failure_type == "runtime_error":
            priority += 3

        priority = max(1, min(100, priority))

        # Extract root cause
        root_cause = "Unknown error"
        if "connection" in error_msg.lower() or "connect" in error_msg.lower():
            root_cause = "Database or service connection error"
        elif "timeout" in error_msg.lower():
            root_cause = "Operation exceeded timeout threshold"
        elif "assertion" in error_msg.lower():
            root_cause = "Test assertion failed - verify expected behavior"
        elif "attributeerror" in error_msg.lower():
            root_cause = "Missing attribute or method - check object initialization"
        elif "keyerror" in error_msg.lower():
            root_cause = "Missing dictionary key - verify data structure"
        elif "typeerror" in error_msg.lower():
            root_cause = "Type mismatch - check function arguments and types"
        elif "valueerror" in error_msg.lower():
            root_cause = "Invalid value - verify input validation logic"
        elif "importerror" in error_msg.lower() or "modulenotfounderror" in error_msg.lower():
            root_cause = "Import error - check module dependencies"

        failures.append(
            {
                "test_id": test_path,
                "test_name": test_name,
                "test_file": test_file,
                "test_line": 0,
                "failure_type": failure_type,
                "severity": severity,
                "diagnostic_context": {
                    "expected": "Test to pass",
                    "actual": error_msg[:500],
                    "stack_trace": error_msg[:1500],
                    "root_cause_hint": root_cause,
                    "fix_priority": priority,
                },
            }
        )

    print(f"\n{'=' * 80}")
    print("PARSED TEST SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total tests: {test_counts['total']}")
    print(f"Passed: {test_counts['passed']}")
    print(f"Failed: {test_counts['failed']}")
    print(f"Skipped: {test_counts['skipped']}")
    print(f"Failures detected: {len(failures)}")

    if failures:
        print("\nTop failures by priority:")
        sorted_failures = sorted(
            failures, key=lambda x: x["diagnostic_context"]["fix_priority"], reverse=True
        )
        for i, f in enumerate(sorted_failures[:5], 1):
            print(f"  {i}. {f['test_id']} (priority: {f['diagnostic_context']['fix_priority']})")

    print(f"{'=' * 80}")

    return test_counts, failures


def parse_coverage(coverage_json_path):
    """Parse coverage JSON file."""
    coverage_data = {
        "overall": 0.0,
        "line_coverage": 0.0,
        "branch_coverage": 0.0,
        "by_module": {},
        "by_file": {},
    }

    if not Path(coverage_json_path).exists():
        print("\nWarning: Coverage file not found at:", coverage_json_path)
        return coverage_data

    try:
        with open(coverage_json_path) as f:
            cov_data = json.load(f)

        # Extract totals
        totals = cov_data.get("totals", {})
        line_pct = totals.get("percent_covered", 0.0)

        coverage_data["line_coverage"] = round(line_pct, 2)
        coverage_data["branch_coverage"] = round(line_pct, 2)  # Use same for both
        coverage_data["overall"] = coverage_data["line_coverage"]

        # Extract per-file coverage
        files = cov_data.get("files", {})
        module_coverages = {}

        for file_path, file_cov in files.items():
            summary = file_cov.get("summary", {})
            pct = round(summary.get("percent_covered", 0.0), 2)

            # Store file coverage
            coverage_data["by_file"][file_path] = pct

            # Group by module (first directory component)
            if "/" in file_path:
                module = file_path.split("/")[0]
                if module not in module_coverages:
                    module_coverages[module] = []
                module_coverages[module].append(pct)

        # Calculate average module coverage
        for module, pcts in module_coverages.items():
            if pcts:
                coverage_data["by_module"][module] = round(sum(pcts) / len(pcts), 2)

        print(f"\n{'=' * 80}")
        print("COVERAGE SUMMARY")
        print(f"{'=' * 80}")
        print(f"Overall coverage: {coverage_data['overall']:.2f}%")
        print(f"Line coverage: {coverage_data['line_coverage']:.2f}%")
        print(f"Branch coverage: {coverage_data['branch_coverage']:.2f}%")
        print("\nModule coverage:")
        for module, pct in sorted(
            coverage_data["by_module"].items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"  {module}: {pct:.2f}%")
        print(f"{'=' * 80}")

    except Exception as e:
        print(f"\nError parsing coverage JSON: {e}")
        import traceback

        traceback.print_exc()

    return coverage_data


def write_results(results, output_file):
    """Write results atomically to JSON file."""
    tmp_file = output_file.with_suffix(".json.tmp")

    try:
        # Write to temporary file
        with open(tmp_file, "w") as f:
            json.dump(results, f, indent=2)

        # Atomic rename
        tmp_file.rename(output_file)

        print(f"\n{'=' * 80}")
        print("RESULTS WRITTEN SUCCESSFULLY")
        print(f"{'=' * 80}")
        print(f"Output file: {output_file}")
        print(f"Status: {results['status']}")
        print(f"Duration: {results['duration_seconds']}s")
        print(
            f"Tests passed: {results['results']['test_counts']['passed']}/{results['results']['test_counts']['total']}"
        )
        print(f"Coverage: {results['results']['coverage']['overall']:.2f}%")
        print(f"Failures: {len(results['results']['failures'])}")
        print(f"{'=' * 80}\n")

        return True

    except Exception as e:
        print(f"\nError writing results: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    sys.exit(main())
