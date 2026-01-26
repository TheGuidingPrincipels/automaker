#!/usr/bin/env python3
"""Add semaphore to all async database methods"""

import re

# Read database.py
with open('short_term_mcp/database.py', 'r') as f:
    content = f.read()

# Pattern to find async methods without semaphore
pattern = r'(    async def async_\w+\([^)]*\)[^:]*:\n        """[^"]*"""\n)(        return await asyncio\.to_thread\()'

# Replacement with semaphore
replacement = r'\1        async with self.semaphore:\n\2'

# Apply replacement
content = re.sub(pattern, replacement, content)

# Write back
with open('short_term_mcp/database.py', 'w') as f:
    f.write(content)

print("✅ Added semaphore to all async database methods")
