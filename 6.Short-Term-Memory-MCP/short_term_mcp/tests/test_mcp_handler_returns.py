"""
Test that MCP tool handlers properly return values.
This test specifically checks for the bug where handlers call impl functions
but don't return the result.
"""

import inspect

import pytest


def test_remove_domain_handler_has_return_statement():
    """
    Test that remove_domain_from_whitelist handler returns the impl result.

    This is a regression test for the bug where the handler called the impl function
    but didn't return its result, causing "No result received from client-side tool execution" errors.
    """
    import short_term_mcp.server as server_module

    # Get the source code of the handler
    # The handler is wrapped, so we need to access it via the module's __dict__ or inspect
    source = inspect.getsource(server_module)

    # Find the remove_domain_from_whitelist function definition
    lines = source.split("\n")
    in_function = False
    function_lines = []
    indent_level = None

    for line in lines:
        if "async def remove_domain_from_whitelist(" in line:
            in_function = True
            indent_level = len(line) - len(line.lstrip())
            continue

        if in_function:
            if line.strip() and not line.strip().startswith("#"):
                current_indent = len(line) - len(line.lstrip())
                # Check if we've exited the function (dedent to same or less level)
                if current_indent <= indent_level and line.strip():
                    break
            function_lines.append(line)

    function_body = "\n".join(function_lines)

    # Check that the impl call has a return statement
    # Look for patterns like: "return await remove_domain_from_whitelist_impl"
    assert (
        "return await remove_domain_from_whitelist_impl" in function_body
        or "return remove_domain_from_whitelist_impl" in function_body
    ), f"Handler must return the result from impl function. Function body:\n{function_body}"
