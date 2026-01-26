#!/usr/bin/env python3
"""Fix indentation issues in database.py"""

with open('short_term_mcp/database.py', 'r') as f:
    lines = f.readlines()

fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    fixed_lines.append(line)

    # If we find "async with self.semaphore:" without proper indentation for next line
    if 'async with self.semaphore:' in line and i + 1 < len(lines):
        next_line = lines[i + 1]
        # If next line starts with 'return' without proper indentation
        if next_line.lstrip().startswith('return ') and not next_line.startswith('            return'):
            # Fix indentation - should be 12 spaces for return inside async with
            fixed_next = '            ' + next_line.lstrip()
            fixed_lines.append(fixed_next)
            i += 2  # Skip the next line since we already added it
            continue

    i += 1

with open('short_term_mcp/database.py', 'w') as f:
    f.writelines(fixed_lines)

print("✅ Fixed indentation issues")
