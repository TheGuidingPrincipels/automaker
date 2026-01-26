#!/usr/bin/env python3
"""
Repository Cleanup Utility for MCP Knowledge Server

This script removes temporary files and artifacts from the repository:
- Python cache files (__pycache__, .pytest_cache)
- Test artifacts (.coverage, test result JSONs)
- System files (.DS_Store, Thumbs.db)
- Temporary documentation files
- Log files

Safety features:
- Dry run mode to preview changes
- File listing before deletion
- Summary of removed files and freed space
"""

import argparse
import contextlib
import os
import shutil
import sys
from pathlib import Path


# Color codes for output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header(message):
    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{message}{Colors.END}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}\n")


def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")


def get_size(path):
    """Get size of file or directory in bytes"""
    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        total = 0
        for item in path.rglob("*"):
            if item.is_file():
                with contextlib.suppress(PermissionError, OSError):
                    total += item.stat().st_size
        return total
    return 0


def format_size(bytes):
    """Format bytes to human-readable size"""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


def find_files_to_clean(root_dir):
    """Find all temporary files that should be cleaned"""
    files_to_remove = {
        "python_cache": [],
        "test_artifacts": [],
        "system_files": [],
        "temp_docs": [],
        "log_files": [],
    }

    root = Path(root_dir)

    # Python cache directories
    for pattern in ["__pycache__", ".pytest_cache", ".tox", ".hypothesis"]:
        for path in root.rglob(pattern):
            if path.is_dir():
                files_to_remove["python_cache"].append(path)

    # Coverage files
    for pattern in [".coverage", "*.coverage", "htmlcov"]:
        for path in root.rglob(pattern):
            if path.exists():
                files_to_remove["test_artifacts"].append(path)

    # Test result files
    test_patterns = [
        "tests/benchmarks/*.json",
        "tests/uat/uat_results.json",
        "tests/uat/uat_execution.log",
        "tests/token_analysis_results.json",
    ]
    for pattern in test_patterns:
        for path in root.glob(pattern):
            if path.exists():
                files_to_remove["test_artifacts"].append(path)

    # System files
    for pattern in [".DS_Store", "Thumbs.db"]:
        for path in root.rglob(pattern):
            if path.exists():
                files_to_remove["system_files"].append(path)

    # Temporary documentation (be careful with these patterns)
    temp_doc_patterns = [
        "*_REPORT.md",
        "*_SUMMARY.md",
        "*_DEBUG*.md",
        "TEST_RESULTS_*.md",
        "SESSION_*.md",
        "TASK_*.md",
        "WEEK_*.md",
    ]
    for pattern in temp_doc_patterns:
        for path in root.glob(pattern):
            if path.is_file():
                files_to_remove["temp_docs"].append(path)

    # Log files (excluding the logs directory used by production)
    for path in root.glob("*.log"):
        if path.is_file() and path.parent == root:
            files_to_remove["log_files"].append(path)

    return files_to_remove


def print_files_to_clean(files_dict):
    """Print summary of files to be cleaned"""
    total_size = 0
    total_count = 0

    for category, files in files_dict.items():
        if files:
            category_size = sum(get_size(f) for f in files)
            total_size += category_size
            total_count += len(files)

            category_name = category.replace("_", " ").title()
            print(f"\n{Colors.BOLD}{category_name}:{Colors.END}")
            print(f"  Files: {len(files)}")
            print(f"  Size: {format_size(category_size)}")

            if len(files) <= 10:
                for f in files:
                    print(f"    - {f.relative_to(Path.cwd())}")
            else:
                for f in files[:5]:
                    print(f"    - {f.relative_to(Path.cwd())}")
                print(f"    ... and {len(files) - 5} more files")

    print(f"\n{Colors.BOLD}Total:{Colors.END}")
    print(f"  Files: {total_count}")
    print(f"  Size: {format_size(total_size)}")
    print()

    return total_size, total_count


def remove_files(files_dict, dry_run=False):
    """Remove the specified files"""
    removed_count = 0
    removed_size = 0
    errors = []

    for _category, files in files_dict.items():
        for path in files:
            try:
                size = get_size(path)

                if dry_run:
                    print_info(f"Would remove: {path.relative_to(Path.cwd())}")
                else:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    print_success(f"Removed: {path.relative_to(Path.cwd())}")

                removed_count += 1
                removed_size += size
            except Exception as e:
                error_msg = f"Failed to remove {path.relative_to(Path.cwd())}: {e}"
                errors.append(error_msg)
                print_error(error_msg)

    return removed_count, removed_size, errors


def main():
    parser = argparse.ArgumentParser(
        description="Repository cleanup utility for MCP Knowledge Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show what would be cleaned
  python cleanup_repository.py --dry-run

  # Clean all temporary files
  python cleanup_repository.py

  # Clean specific categories
  python cleanup_repository.py --python-cache
  python cleanup_repository.py --test-artifacts
  python cleanup_repository.py --system-files

  # Clean without confirmation
  python cleanup_repository.py --yes
        """,
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be deleted without making changes"
    )
    parser.add_argument("--python-cache", action="store_true", help="Clean only Python cache files")
    parser.add_argument("--test-artifacts", action="store_true", help="Clean only test artifacts")
    parser.add_argument(
        "--system-files", action="store_true", help="Clean only system files (.DS_Store, etc)"
    )
    parser.add_argument(
        "--temp-docs", action="store_true", help="Clean only temporary documentation"
    )
    parser.add_argument("--log-files", action="store_true", help="Clean only log files")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    args = parser.parse_args()

    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print_header("MCP Knowledge Server - Repository Cleanup Utility")

    # Find files to clean
    all_files = find_files_to_clean(project_root)

    # Filter by category if specified
    if any(
        [args.python_cache, args.test_artifacts, args.system_files, args.temp_docs, args.log_files]
    ):
        filtered_files = {}
        if args.python_cache:
            filtered_files["python_cache"] = all_files["python_cache"]
        if args.test_artifacts:
            filtered_files["test_artifacts"] = all_files["test_artifacts"]
        if args.system_files:
            filtered_files["system_files"] = all_files["system_files"]
        if args.temp_docs:
            filtered_files["temp_docs"] = all_files["temp_docs"]
        if args.log_files:
            filtered_files["log_files"] = all_files["log_files"]
        files_to_clean = filtered_files
    else:
        files_to_clean = all_files

    # Check if there's anything to clean
    total_files = sum(len(files) for files in files_to_clean.values())
    if total_files == 0:
        print_success("Repository is already clean! No files to remove.")
        return 0

    # Show what will be cleaned
    print_info("Files to be cleaned:")
    total_size, total_count = print_files_to_clean(files_to_clean)

    if args.dry_run:
        print_warning("DRY RUN MODE - No changes will be made")
        print()
        return 0

    # Confirmation prompt
    if not args.yes:
        response = input(
            f"{Colors.YELLOW}⚠️  Remove {total_count} files ({format_size(total_size)})? (yes/no): {Colors.END}"
        )
        if response.lower() != "yes":
            print_info("Cleanup cancelled")
            return 0

    # Perform cleanup
    print_info("Starting cleanup...")
    removed_count, removed_size, errors = remove_files(files_to_clean, dry_run=False)

    # Summary
    print_header("Cleanup Summary")
    print_success(f"Removed {removed_count} files")
    print_success(f"Freed {format_size(removed_size)} of disk space")

    if errors:
        print_warning(f"{len(errors)} errors occurred during cleanup")
        return 1

    print_info("Repository cleanup completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
