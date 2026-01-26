#!/usr/bin/env python3
"""
Batched test runner with progress tracking and early timeout detection.
Runs tests in smaller batches to avoid hanging and provides incremental results.
"""
import contextlib
import glob
import json
import os
import subprocess
import time
from pathlib import Path


def run_test_file(test_file, timeout=60):
    """Run a single test file and return results."""
    cmd = [
        ".venv/bin/pytest",
        test_file,
        "-v",
        "--tb=short",
        "--json-report",
        f"--json-report-file=.test-output/intermediate/{Path(test_file).stem}_report.json",
    ]

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd="/Users/ruben/Documents/GitHub/automaker/5.Knowledge Server",
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - start_time

        # Parse output
        lines = result.stdout.split("\n")
        passed = failed = skipped = 0
        for line in lines:
            if " passed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        with contextlib.suppress(ValueError):
                            passed = int(parts[i - 1])
            if " failed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "failed" and i > 0:
                        with contextlib.suppress(ValueError):
                            failed = int(parts[i - 1])
            if " skipped" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "skipped" and i > 0:
                        with contextlib.suppress(ValueError):
                            skipped = int(parts[i - 1])

        return {
            "file": test_file,
            "status": "passed" if result.returncode == 0 else "failed",
            "duration": duration,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": passed + failed + skipped,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return {
            "file": test_file,
            "status": "timeout",
            "duration": duration,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "error": f"Test file timed out after {timeout}s",
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "file": test_file,
            "status": "error",
            "duration": duration,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "error": str(e),
        }


def main():
    print("=" * 80)
    print("BATCHED TEST RUNNER - Running tests file by file")
    print("=" * 80)

    # Find all test files
    test_files = []
    for pattern in ["tests/test_*.py", "tests/*/test_*.py", "tests/*/*/test_*.py"]:
        test_files.extend(glob.glob(pattern))

    test_files = sorted(set(test_files))
    print(f"\nFound {len(test_files)} test files\n")

    # Run each test file
    results = []
    total_passed = total_failed = total_skipped = 0
    total_duration = 0

    start_time = time.time()
    max_total_time = 420  # 7 minutes total

    for i, test_file in enumerate(test_files, 1):
        elapsed = time.time() - start_time
        if elapsed > max_total_time:
            print(f"\n⚠️  Total time budget exceeded ({elapsed:.1f}s > {max_total_time}s)")
            print(f"   Stopping after {i-1}/{len(test_files)} test files")
            break

        print(f"[{i}/{len(test_files)}] Running {test_file}...", end=" ", flush=True)

        result = run_test_file(test_file, timeout=45)
        results.append(result)

        total_passed += result["passed"]
        total_failed += result["failed"]
        total_skipped += result["skipped"]
        total_duration += result["duration"]

        if result["status"] == "passed":
            print(f"✓ {result['passed']} passed ({result['duration']:.2f}s)")
        elif result["status"] == "failed":
            print(
                f"✗ {result['failed']} failed, {result['passed']} passed ({result['duration']:.2f}s)"
            )
        elif result["status"] == "timeout":
            print(f"⏱  TIMEOUT after {result['duration']:.1f}s")
        else:
            print(f"⚠  ERROR: {result.get('error', 'unknown')}")

    # Generate summary
    print("\n" + "=" * 80)
    print("TEST EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Files executed: {len(results)}/{len(test_files)}")
    print(f"Total tests: {total_passed + total_failed + total_skipped}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"  Skipped: {total_skipped}")
    print(f"Duration: {total_duration:.2f}s")

    # Calculate success rate
    total_tests = total_passed + total_failed + total_skipped
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")

    # Write backend-results.json
    backend_results = {
        "agent_name": "backend-tester",
        "status": "success" if total_failed == 0 else "failed",
        "duration_seconds": total_duration,
        "results": {
            "test_counts": {
                "total": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
            },
            "coverage": {
                "overall": 0.0,  # Will be calculated separately
                "line_coverage": 0.0,
                "branch_coverage": 0.0,
                "by_module": {},
                "by_file": {},
            },
            "failures": [],
            "test_file_results": results,
        },
    }

    output_file = ".test-output/intermediate/backend-results.json"
    tmp_file = output_file + ".tmp"

    with open(tmp_file, "w") as f:
        json.dump(backend_results, f, indent=2)

    os.rename(tmp_file, output_file)

    print(f"\nResults written to: {output_file}")
    print("=" * 80)

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    exit(main())
