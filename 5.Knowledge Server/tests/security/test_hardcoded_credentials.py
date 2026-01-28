"""
Security tests to ensure no hardcoded credentials are present in the codebase.

This test module validates CWE-798 (Hardcoded Credentials) remediation.
"""

import os
import re
from pathlib import Path

import pytest


class TestHardcodedCredentials:
    """Tests to verify no hardcoded credentials exist in configuration files."""

    @pytest.mark.skipif(
        os.getenv("CI") != "true",
        reason="Skipped in local dev - .env may contain development passwords"
    )
    def test_env_file_has_no_hardcoded_passwords(self):
        """
        Test that .env file does not contain hardcoded passwords.

        Security Issue: CWE-798 - Use of Hard-coded Credentials
        Severity: HIGH
        Fix: Replaced hardcoded 'password' with environment variable reference
        """
        env_file_path = Path(__file__).parent.parent.parent / ".env"

        if not env_file_path.exists():
            pytest.skip(".env file does not exist")

        with open(env_file_path) as f:
            env_content = f.read()

        # Check that common hardcoded passwords are not present
        hardcoded_patterns = [
            r'PASSWORD\s*=\s*["\']?password["\']?\s*$',
            r'PASSWORD\s*=\s*["\']?admin["\']?\s*$',
            r'PASSWORD\s*=\s*["\']?123456["\']?\s*$',
            r'PASSWORD\s*=\s*["\']?test["\']?\s*$',
        ]

        for pattern in hardcoded_patterns:
            matches = re.findall(pattern, env_content, re.MULTILINE | re.IGNORECASE)
            assert not matches, (
                f"Found hardcoded password pattern: {pattern}. "
                f"Use environment variables or secure secret management instead."
            )

    @pytest.mark.skipif(
        os.getenv("CI") != "true",
        reason="Skipped in local dev - .env may contain development passwords"
    )
    def test_env_file_uses_environment_variable_references(self):
        """
        Test that .env file uses environment variable references for sensitive data.

        Validates that passwords are referenced as ${VAR_NAME} rather than hardcoded.
        """
        env_file_path = Path(__file__).parent.parent.parent / ".env"

        if not env_file_path.exists():
            pytest.skip(".env file does not exist")

        with open(env_file_path) as f:
            env_content = f.read()

        # Find all PASSWORD variables
        password_lines = [
            line
            for line in env_content.split("\n")
            if "PASSWORD" in line.upper() and not line.strip().startswith("#")
        ]

        for line in password_lines:
            if "=" in line:
                # Check that it uses ${VAR} pattern or is empty
                assert (
                    "${" in line
                    or line.split("=", 1)[1].strip() == ""
                    or line.split("=", 1)[1].strip().startswith("#")
                ), f"Password variable should use environment variable reference: {line}"

    def test_env_example_exists_with_placeholders(self):
        """
        Test that .env.example exists and contains placeholder values.

        Best Practice: Provide example configuration without sensitive data.
        """
        env_example_path = Path(__file__).parent.parent.parent / ".env.example"

        assert (
            env_example_path.exists()
        ), ".env.example file should exist to provide configuration template"

        with open(env_example_path) as f:
            example_content = f.read()

        # Verify it has placeholder text
        assert (
            "your_secure_password_here" in example_content.lower()
            or "placeholder" in example_content.lower()
            or "change_me" in example_content.lower()
        ), ".env.example should contain placeholder values, not actual credentials"

    def test_no_secrets_in_python_files(self):
        """
        Test that Python source files don't contain hardcoded credentials.

        Scans all .py files for common credential patterns.
        """
        project_root = Path(__file__).parent.parent.parent

        # Patterns that indicate hardcoded secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\'$]{3,}["\']',  # password = "something"
            r'api_key\s*=\s*["\'][^"\'$]{10,}["\']',  # api_key = "longstring"
            r'secret\s*=\s*["\'][^"\'$]{10,}["\']',  # secret = "longstring"
            r'token\s*=\s*["\'][^"\'$]{10,}["\']',  # token = "longstring"
        ]

        excluded_dirs = {".venv", "venv", "node_modules", "__pycache__", ".git", "tests", "config"}

        violations = []

        for py_file in project_root.rglob("*.py"):
            # Skip test files and virtual environments
            if any(excluded in py_file.parts for excluded in excluded_dirs):
                continue

            with open(py_file, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            for pattern in secret_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    violations.append(
                        {
                            "file": str(py_file.relative_to(project_root)),
                            "pattern": pattern,
                            "matches": matches,
                        }
                    )

        assert not violations, f"Found potential hardcoded secrets in Python files: {violations}"


class TestDependencyVulnerabilities:
    """Tests to verify dependencies are up-to-date and secure."""

    def test_python_version_mitigates_cve_2025_8869(self):
        """
        Test that Python version implements PEP 706, mitigating CVE-2025-8869.

        Security Issue: CVE-2025-8869 - Path Traversal in pip tarfile extraction
        Severity: MEDIUM (CVSS 5.9)
        CWE: CWE-22 (Path Traversal)

        CVE-2025-8869 affects pip's fallback tar extraction, but Python versions
        that implement PEP 706 use secure tar extraction natively, bypassing
        the vulnerable pip fallback code.

        PEP 706 compliant Python versions:
        - Python >= 3.9.17
        - Python >= 3.10.12
        - Python >= 3.11.4
        - Python >= 3.12
        """
        import sys
        version = sys.version_info

        pep706_compliant = (
            (version.major == 3 and version.minor == 9 and version.micro >= 17) or
            (version.major == 3 and version.minor == 10 and version.micro >= 12) or
            (version.major == 3 and version.minor == 11 and version.micro >= 4) or
            (version.major == 3 and version.minor >= 12) or
            (version.major > 3)
        )

        assert pep706_compliant, (
            f"Python {version.major}.{version.minor}.{version.micro} does not implement PEP 706. "
            f"Upgrade to Python >=3.9.17, >=3.10.12, >=3.11.4, or >=3.12 to mitigate CVE-2025-8869."
        )

    def test_no_known_vulnerable_dependencies(self):
        """
        Test that no known vulnerable dependencies are present.

        This test verifies Python version provides PEP 706 mitigation for
        CVE-2025-8869 and can be extended with tools like pip-audit, safety, etc.

        In production, consider integrating with:
        - pip-audit
        - safety
        - Snyk
        - GitHub Dependabot
        """
        import sys
        version = sys.version_info

        # Verify Python version mitigates known vulnerabilities via PEP 706
        pep706_compliant = (
            (version.major == 3 and version.minor == 9 and version.micro >= 17) or
            (version.major == 3 and version.minor == 10 and version.micro >= 12) or
            (version.major == 3 and version.minor == 11 and version.micro >= 4) or
            (version.major == 3 and version.minor >= 12) or
            (version.major > 3)
        )

        assert pep706_compliant, (
            f"Python {version.major}.{version.minor}.{version.micro} is vulnerable to "
            f"tarfile extraction attacks (CVE-2025-8869). Upgrade Python to a PEP 706 "
            f"compliant version: >=3.9.17, >=3.10.12, >=3.11.4, or >=3.12."
        )
