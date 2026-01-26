#!/usr/bin/env python3
"""
UAT Readiness Check for MCP Knowledge Server
Verifies all prerequisites before running UAT tests.
"""

import asyncio
import os
import sys
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed yet


class ReadinessCheck:
    """Pre-flight checks for UAT execution."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0

    def print_header(self, text: str):
        """Print section header."""
        print(f"\n{'=' * 60}")
        print(f"  {text}")
        print(f"{'=' * 60}")

    def print_check(self, name: str, passed: bool, details: str = ""):
        """Print check result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {name}")
        if details:
            print(f"     {details}")

        if passed:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

    def print_warning(self, message: str):
        """Print warning message."""
        print(f"⚠️  WARNING: {message}")
        self.warnings += 1

    def check_python_version(self) -> bool:
        """Check Python version is 3.11+."""
        version = sys.version_info
        passed = version >= (3, 11)
        self.print_check(
            "Python version (3.11+)",
            passed,
            f"Found: {version.major}.{version.minor}.{version.micro}",
        )
        return passed

    def check_project_structure(self) -> bool:
        """Check required project files and directories exist."""
        project_root = Path(__file__).parent.parent.parent
        required_paths = [
            ("tools", True),
            ("services", True),
            ("models", True),
            ("tests", True),
            (".env", False),
        ]

        all_passed = True
        for path_name, is_dir in required_paths:
            path = project_root / path_name
            exists = path.is_dir() if is_dir else path.is_file()

            if not exists:
                self.print_check(f"Path exists: {path_name}", False, f"Not found: {path}")
                all_passed = False
            elif self.verbose:
                self.print_check(f"Path exists: {path_name}", True)

        if all_passed and not self.verbose:
            self.print_check("Project structure", True, "All required paths exist")

        return all_passed

    def check_environment_file(self) -> bool:
        """Check .env file exists and has required variables."""
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"

        if not env_file.exists():
            self.print_check(".env file", False, "File not found")
            return False

        # Check for required variables
        required_vars = [
            "NEO4J_URI",
            "NEO4J_USER",
            "NEO4J_PASSWORD",
            "CHROMA_PERSIST_DIRECTORY",
            "EVENT_STORE_PATH",
        ]

        with open(env_file) as f:
            env_content = f.read()

        missing_vars = []
        for var in required_vars:
            if var not in env_content:
                missing_vars.append(var)

        if missing_vars:
            self.print_check(
                ".env configuration",
                False,
                f"Missing variables: {', '.join(missing_vars)}",
            )
            return False
        else:
            self.print_check(".env configuration", True, "All required variables present")
            return True

    def check_dependencies(self) -> bool:
        """Check required Python packages are installed."""
        required_packages = [
            ("neo4j", "neo4j"),
            ("chromadb", "chromadb"),
            ("pydantic", "pydantic"),
            ("python-dotenv", "dotenv"),
        ]

        all_installed = True
        missing_packages = []

        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
            except ImportError:
                missing_packages.append(package_name)
                all_installed = False

        if all_installed:
            self.print_check("Python dependencies", True, "All required packages installed")
        else:
            self.print_check(
                "Python dependencies",
                False,
                f"Missing: {', '.join(missing_packages)}",
            )

        return all_installed

    async def check_neo4j_connection(self) -> bool:
        """Check Neo4j database connection."""
        try:
            from services.neo4j_service import Neo4jService

            # Initialize with environment variables
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password")

            service = Neo4jService(uri=uri, user=user, password=password)

            # Connect to Neo4j
            if not service.connect():
                self.print_check("Neo4j connection", False, "Failed to connect")
                return False

            # Try to ping Neo4j
            try:
                with service.driver.session() as session:
                    result = session.run("RETURN 1 as test")
                    result.single()
                self.print_check("Neo4j connection", True, f"Connected to {uri}")
                service.close()
                return True
            except Exception as e:
                self.print_check("Neo4j connection", False, str(e))
                service.close()
                return False
        except Exception as e:
            self.print_check("Neo4j connection", False, f"Failed to initialize: {e!s}")
            return False

    async def check_chromadb(self) -> bool:
        """Check ChromaDB accessibility."""
        try:

            from services.chromadb_service import ChromaDbService

            # Get persist directory from environment
            persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")

            service = ChromaDbService()
            service.config.persist_directory = persist_dir

            # Connect to ChromaDB
            if not service.connect():
                self.print_check("ChromaDB connection", False, "Failed to connect")
                return False

            # Try to access collection
            try:
                collection = service.get_collection()
                count = collection.count()
                self.print_check(
                    "ChromaDB connection", True, f"Collection accessible, {count} items"
                )
                return True
            except Exception as e:
                self.print_check("ChromaDB connection", False, str(e))
                return False
        except Exception as e:
            self.print_check("ChromaDB connection", False, f"Failed to initialize: {e!s}")
            return False

    def check_event_store(self) -> bool:
        """Check EventStore database file."""
        event_store_path = os.getenv("EVENT_STORE_PATH", "data/event_store.db")
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / event_store_path

        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            self.print_check("EventStore database", True, f"Found at {db_path} ({size_mb:.2f} MB)")
            return True
        else:
            self.print_warning(f"EventStore database not found at {db_path} (will be created)")
            return True  # Not a failure, will be created

    def check_test_data(self) -> bool:
        """Check UAT test data file exists."""
        test_data_file = Path(__file__).parent / "test_data.json"

        if not test_data_file.exists():
            self.print_check("UAT test data", False, f"Not found: {test_data_file}")
            return False

        # Try to load and validate JSON
        try:
            import json

            with open(test_data_file) as f:
                data = json.load(f)

            concepts_count = len(data.get("concepts", []))
            relationships_count = len(data.get("relationships", []))

            if concepts_count == 0:
                self.print_check("UAT test data", False, "No concepts found in test data")
                return False

            self.print_check(
                "UAT test data",
                True,
                f"{concepts_count} concepts, {relationships_count} relationships",
            )
            return True
        except Exception as e:
            self.print_check("UAT test data", False, f"Invalid JSON: {e!s}")
            return False

    def check_disk_space(self) -> bool:
        """Check available disk space."""
        try:
            import shutil

            project_root = Path(__file__).parent.parent.parent
            stat = shutil.disk_usage(project_root)
            free_gb = stat.free / (1024**3)

            # Warn if less than 1GB free
            if free_gb < 1:
                self.print_warning(f"Low disk space: {free_gb:.2f} GB free")
                self.print_check("Disk space", True, f"{free_gb:.2f} GB free (warning: low)")
                return True
            else:
                self.print_check("Disk space", True, f"{free_gb:.2f} GB free")
                return True
        except Exception as e:
            self.print_warning(f"Could not check disk space: {e!s}")
            return True  # Not critical

    def check_monitoring_scripts(self) -> bool:
        """Check monitoring scripts exist."""
        project_root = Path(__file__).parent.parent.parent
        monitoring_dir = project_root / "monitoring"

        if not monitoring_dir.exists():
            self.print_warning("Monitoring directory not found")
            return True  # Not critical for UAT

        scripts = ["health_check.py", "resource_monitor.py"]
        all_found = True

        for script in scripts:
            if not (monitoring_dir / script).exists():
                all_found = False
                if self.verbose:
                    self.print_warning(f"Monitoring script not found: {script}")

        if all_found:
            self.print_check("Monitoring scripts", True, "All scripts present")
        else:
            self.print_warning("Some monitoring scripts missing (not critical)")

        return True  # Not critical for UAT

    def check_backup_scripts(self) -> bool:
        """Check backup scripts exist."""
        project_root = Path(__file__).parent.parent.parent
        backup_dir = project_root / "backup"

        if not backup_dir.exists():
            self.print_warning("Backup directory not found")
            return True  # Not critical for UAT

        scripts = ["backup_all.sh", "restore_all.sh"]
        all_found = True

        for script in scripts:
            if not (backup_dir / script).exists():
                all_found = False
                if self.verbose:
                    self.print_warning(f"Backup script not found: {script}")

        if all_found:
            self.print_check("Backup scripts", True, "All scripts present")
        else:
            self.print_warning("Some backup scripts missing (not critical)")

        return True  # Not critical for UAT

    async def run_all_checks(self) -> bool:
        """Run all readiness checks."""
        self.print_header("UAT Readiness Check")

        # Environment checks
        self.print_header("Environment Checks")
        self.check_python_version()
        self.check_project_structure()
        self.check_environment_file()
        self.check_dependencies()

        # Database checks
        self.print_header("Database Checks")
        await self.check_neo4j_connection()
        await self.check_chromadb()
        self.check_event_store()

        # Infrastructure checks
        self.print_header("Infrastructure Checks")
        self.check_monitoring_scripts()
        self.check_backup_scripts()
        self.check_disk_space()

        # UAT-specific checks
        self.print_header("UAT-Specific Checks")
        self.check_test_data()

        # Summary
        self.print_header("Readiness Check Summary")
        total_checks = self.checks_passed + self.checks_failed
        pass_rate = (self.checks_passed / total_checks * 100) if total_checks > 0 else 0

        print(f"Total Checks: {total_checks}")
        print(f"Passed: {self.checks_passed} ✅")
        print(f"Failed: {self.checks_failed} ❌")
        print(f"Warnings: {self.warnings} ⚠️")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print()

        if self.checks_failed == 0:
            print("🎉 SYSTEM READY FOR UAT! 🎉")
            print("\nYou can now run: python tests/uat/uat_runner.py")
            return True
        else:
            print("❌ SYSTEM NOT READY FOR UAT")
            print("\nPlease resolve the failed checks above before running UAT.")
            return False


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Check UAT readiness for MCP Knowledge Server")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    checker = ReadinessCheck(verbose=args.verbose)
    ready = await checker.run_all_checks()

    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    asyncio.run(main())
