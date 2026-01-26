#!/usr/bin/env python3
"""Script to update all remaining tool implementations to use async database operations"""

import re

# Read the file
with open('short_term_mcp/tools_impl.py', 'r') as f:
    content = f.read()

# Patterns to replace
replacements = [
    # Database method replacements
    (r'db\.get_session\(', r'await db.async_get_session('),
    (r'db\.create_session\(', r'await db.async_create_session('),
    (r'db\.get_concept\(', r'await db.async_get_concept('),
    (r'db\.create_concept\(', r'await db.async_create_concept('),
    (r'db\.update_concept_status\(', r'await db.async_update_concept_status('),
    (r'db\.get_concepts_by_session\(', r'await db.async_get_concepts_by_session('),
    (r'db\.store_stage_data\(', r'await db.async_store_stage_data('),
    (r'db\.get_stage_data\(', r'await db.async_get_stage_data('),
    (r'db\.mark_session_complete\(', r'await db.async_mark_session_complete('),
    (r'db\.clear_old_sessions\(', r'await db.async_clear_old_sessions('),
    (r'db\.get_todays_session\(', r'await db.async_get_todays_session('),
    (r'db\.search_concepts\(', r'await db.async_search_concepts('),
    (r'db\.add_question_to_concept\(', r'await db.async_add_question_to_concept('),
    (r'db\.update_concept_data\(', r'await db.async_update_concept_data('),
    (r'db\.get_concept_with_all_data\(', r'await db.async_get_concept_with_all_data('),
    (r'db\.get_metrics\(\)', r'await db.async_get_metrics()'),
    (r'db\.get_errors\(', r'await db.async_get_errors('),
    (r'db\.get_database_size\(\)', r'await db.async_get_database_size()'),
    (r'db\.get_health_status\(\)', r'await db.async_get_health_status()'),

    # Cache method replacements
    (r'cache\.get\(', r'await cache.get('),
    (r'cache\.set\(', r'await cache.set('),
    (r'cache\.clear\(\)', r'await cache.clear()'),
]

# Apply replacements
for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Write back
with open('short_term_mcp/tools_impl.py', 'w') as f:
    f.write(content)

print("✅ Updated all database and cache calls to async")
print("Note: Still need to wrap functions not yet wrapped in with_timeout()")
