# URL Testing Protocol for Claude Desktop

**Purpose**: Comprehensive testing of the new `source_urls` feature in Knowledge MCP server.

**Test Date**: 2025-11-10
**Feature**: Optional `source_urls` parameter for create_concept and update_concept tools
**Tester**: Claude Desktop (using MCP tools)

---

## 🎯 **Testing Objectives**

Verify that:

1. ✅ Concepts can be created WITH source URLs
2. ✅ Concepts can be created WITHOUT source URLs (backward compatibility)
3. ✅ Source URLs are stored and persisted correctly
4. ✅ Source URLs can be retrieved via get_concept
5. ✅ Source URLs can be updated/modified
6. ✅ Invalid JSON is rejected with clear error messages
7. ✅ URLs persist across multiple retrievals

---

## 📋 **Test Protocol Overview**

This protocol contains **10 test cases** organized into 4 test suites:

- **Suite 1**: Create Concepts with URLs (3 tests)
- **Suite 2**: Retrieve and Verify URLs (2 tests)
- **Suite 3**: Update URLs (3 tests)
- **Suite 4**: Validation and Error Handling (2 tests)

**Estimated Duration**: 15-20 minutes

---

## 🧪 **TEST SUITE 1: Create Concepts with URLs**

### **Test 1.1: Create Concept with Single URL (Official Source)**

**Objective**: Verify concept creation with one official source URL

**Steps**:

1. Call `create_concept` with the following parameters:

   ```json
   {
     "name": "Python AsyncIO Test",
     "explanation": "Asynchronous I/O framework in Python for concurrent programming",
     "area": "Programming",
     "topic": "Python",
     "subtopic": "Concurrency",
     "source_urls": "[{\"url\": \"https://docs.python.org/3/library/asyncio.html\", \"title\": \"asyncio — Asynchronous I/O\", \"quality_score\": 1.0, \"domain_category\": \"official\"}]"
   }
   ```

2. **Expected Result**:
   - `success`: true
   - `concept_id`: (save this for later tests)
   - `message`: "Created"

3. **Verification**:
   - Record the `concept_id` returned
   - Confirm no error messages

**Pass Criteria**: ✅ Concept created successfully with concept_id returned

---

### **Test 1.2: Create Concept with Multiple URLs (Mixed Sources)**

**Objective**: Verify concept creation with multiple source URLs of different quality levels

**Steps**:

1. Call `create_concept` with the following parameters:

   ```json
   {
     "name": "React Hooks Test",
     "explanation": "React Hooks are functions that let you use state and lifecycle features in functional components",
     "area": "Web Development",
     "topic": "React",
     "source_urls": "[{\"url\": \"https://react.dev/reference/react\", \"title\": \"React Reference\", \"quality_score\": 1.0, \"domain_category\": \"official\"}, {\"url\": \"https://www.freecodecamp.org/news/react-hooks-cheatsheet/\", \"title\": \"React Hooks Cheatsheet\", \"quality_score\": 0.8, \"domain_category\": \"in_depth\"}, {\"url\": \"https://github.com/facebook/react\", \"title\": \"React GitHub\", \"quality_score\": 0.6, \"domain_category\": \"authoritative\"}]"
   }
   ```

2. **Expected Result**:
   - `success`: true
   - `concept_id`: (save this for later tests)

3. **Verification**:
   - Record the `concept_id` returned
   - Note: This concept has 3 URLs (official, in_depth, authoritative)

**Pass Criteria**: ✅ Concept created successfully with multiple URLs

---

### **Test 1.3: Create Concept WITHOUT URLs (Backward Compatibility)**

**Objective**: Verify that omitting source_urls parameter still works (backward compatibility)

**Steps**:

1. Call `create_concept` with the following parameters (NO source_urls):

   ```json
   {
     "name": "Docker Containers Test",
     "explanation": "Docker is a platform for developing, shipping, and running applications in containers",
     "area": "DevOps",
     "topic": "Containerization"
   }
   ```

2. **Expected Result**:
   - `success`: true
   - `concept_id`: (save this for later tests)

3. **Verification**:
   - Concept created successfully WITHOUT source_urls parameter
   - No errors or warnings

**Pass Criteria**: ✅ Concept created successfully without source_urls (backward compatible)

---

## 🔍 **TEST SUITE 2: Retrieve and Verify URLs**

### **Test 2.1: Retrieve Concept with URLs and Verify Content**

**Objective**: Verify that stored URLs are returned correctly when retrieving a concept

**Steps**:

1. Use the `concept_id` from **Test 1.1** (Python AsyncIO Test)
2. Call `get_concept` with:

   ```json
   {
     "concept_id": "[concept_id from Test 1.1]"
   }
   ```

3. **Expected Result**:
   - `success`: true
   - `concept.name`: "Python AsyncIO Test"
   - `concept.source_urls`: Should contain the URL array

4. **Detailed Verification**:
   - Check that `concept.source_urls` exists
   - Verify it's an array with 1 element
   - Verify the URL is: `"https://docs.python.org/3/library/asyncio.html"`
   - Verify `title`: "asyncio — Asynchronous I/O"
   - Verify `quality_score`: 1.0
   - Verify `domain_category`: "official"

**Pass Criteria**: ✅ source_urls returned correctly with all fields intact

---

### **Test 2.2: Retrieve Concept with Multiple URLs**

**Objective**: Verify that multiple URLs are stored and retrieved correctly

**Steps**:

1. Use the `concept_id` from **Test 1.2** (React Hooks Test)
2. Call `get_concept` with:

   ```json
   {
     "concept_id": "[concept_id from Test 1.2]"
   }
   ```

3. **Expected Result**:
   - `success`: true
   - `concept.source_urls`: Array with 3 elements

4. **Detailed Verification**:
   - Count URLs: Should be exactly 3
   - Verify first URL domain: `react.dev`
   - Verify second URL domain: `freecodecamp.org`
   - Verify third URL domain: `github.com`
   - Verify quality scores: 1.0, 0.8, 0.6
   - Verify categories: "official", "in_depth", "authoritative"

**Pass Criteria**: ✅ All 3 URLs returned correctly with correct ordering and metadata

---

### **Test 2.3: Retrieve Concept WITHOUT URLs**

**Objective**: Verify that concepts without URLs are retrieved normally

**Steps**:

1. Use the `concept_id` from **Test 1.3** (Docker Containers Test)
2. Call `get_concept` with:

   ```json
   {
     "concept_id": "[concept_id from Test 1.3]"
   }
   ```

3. **Expected Result**:
   - `success`: true
   - `concept.name`: "Docker Containers Test"
   - `concept.source_urls`: Should be null, undefined, or empty array

4. **Verification**:
   - Concept retrieved successfully
   - No error about missing source_urls field
   - Other fields (name, explanation, area, topic) present

**Pass Criteria**: ✅ Concept without URLs retrieved successfully

---

## 🔄 **TEST SUITE 3: Update URLs**

### **Test 3.1: Add URLs to Existing Concept (Initially Without URLs)**

**Objective**: Verify that URLs can be added to a concept that was created without them

**Steps**:

1. Use the `concept_id` from **Test 1.3** (Docker Containers Test - has no URLs)
2. Call `update_concept` with:

   ```json
   {
     "concept_id": "[concept_id from Test 1.3]",
     "source_urls": "[{\"url\": \"https://docs.docker.com\", \"title\": \"Docker Documentation\", \"quality_score\": 1.0, \"domain_category\": \"official\"}]"
   }
   ```

3. **Expected Result**:
   - `success`: true
   - `updated_fields`: Should include "source_urls"

4. **Verification**:
   - Call `get_concept` again with the same concept_id
   - Verify `source_urls` now contains the Docker docs URL
   - Verify other fields (name, explanation) unchanged

**Pass Criteria**: ✅ URLs successfully added to concept that previously had none

---

### **Test 3.2: Modify Existing URLs (Replace)**

**Objective**: Verify that existing URLs can be replaced with new ones

**Steps**:

1. Use the `concept_id` from **Test 1.1** (Python AsyncIO Test - has 1 URL)
2. Call `update_concept` with NEW URLs:

   ```json
   {
     "concept_id": "[concept_id from Test 1.1]",
     "source_urls": "[{\"url\": \"https://realpython.com/async-io-python/\", \"title\": \"Async IO in Python\", \"quality_score\": 0.8, \"domain_category\": \"in_depth\"}, {\"url\": \"https://docs.python.org/3/library/asyncio.html\", \"title\": \"Official asyncio docs\", \"quality_score\": 1.0, \"domain_category\": \"official\"}]"
   }
   ```

3. **Expected Result**:
   - `success`: true
   - `updated_fields`: Should include "source_urls"

4. **Verification**:
   - Call `get_concept` again
   - Verify `source_urls` now has 2 URLs (was 1 before)
   - Verify the new Real Python URL is present
   - Verify the official docs URL still exists

**Pass Criteria**: ✅ URLs successfully updated/replaced

---

### **Test 3.3: Update Other Fields Without Touching URLs**

**Objective**: Verify that updating other fields doesn't affect source_urls

**Steps**:

1. Use the `concept_id` from **Test 1.2** (React Hooks Test - has 3 URLs)
2. Call `update_concept` to change only the explanation (NO source_urls parameter):

   ```json
   {
     "concept_id": "[concept_id from Test 1.2]",
     "explanation": "React Hooks are powerful functions that enable state and lifecycle features in functional components, replacing class-based patterns."
   }
   ```

3. **Expected Result**:
   - `success`: true
   - `updated_fields`: Should include "explanation" but NOT "source_urls"

4. **Verification**:
   - Call `get_concept` again
   - Verify `explanation` has changed
   - Verify `source_urls` still has 3 URLs (unchanged)
   - All 3 URLs should be exactly the same as before

**Pass Criteria**: ✅ Explanation updated, URLs preserved unchanged

---

## ⚠️ **TEST SUITE 4: Validation and Error Handling**

### **Test 4.1: Invalid JSON Rejected**

**Objective**: Verify that invalid JSON in source_urls is rejected with clear error

**Steps**:

1. Call `create_concept` with INVALID JSON in source_urls:

   ```json
   {
     "name": "Invalid JSON Test",
     "explanation": "This should fail",
     "source_urls": "not-valid-json-string"
   }
   ```

2. **Expected Result**:
   - `success`: false
   - `error_type`: "validation_error"
   - `error`: Should mention "JSON" or "invalid"

3. **Verification**:
   - Error response returned (not success)
   - Error message is clear and actionable
   - No concept created in the database

**Pass Criteria**: ✅ Invalid JSON rejected with clear error message

---

### **Test 4.2: Wrong Data Type Rejected (Object Instead of Array)**

**Objective**: Verify that source_urls must be an array, not an object

**Steps**:

1. Call `create_concept` with JSON OBJECT instead of ARRAY:

   ```json
   {
     "name": "Wrong Type Test",
     "explanation": "This should fail",
     "source_urls": "{\"url\": \"https://example.com\"}"
   }
   ```

2. **Expected Result**:
   - `success`: false
   - `error_type`: "validation_error"
   - `error`: Should mention "array" or "list"

3. **Verification**:
   - Error response returned
   - Error message explains that source_urls must be an array
   - No concept created

**Pass Criteria**: ✅ Object rejected, array required

---

### **Test 4.3: Missing Required "url" Field Rejected**

**Objective**: Verify that each URL object must have a "url" field

**Steps**:

1. Call `create_concept` with URL object MISSING the required "url" field:

   ```json
   {
     "name": "Missing URL Field Test",
     "explanation": "This should fail",
     "source_urls": "[{\"title\": \"Example\", \"quality_score\": 0.8}]"
   }
   ```

2. **Expected Result**:
   - `success`: false
   - `error_type`: "validation_error"
   - `error`: Should mention "url" field is required

3. **Verification**:
   - Error response returned
   - Error message explains that "url" field is required
   - No concept created

**Pass Criteria**: ✅ Missing "url" field rejected with clear error

---

## 🔁 **TEST SUITE 5: Persistence Verification**

### **Test 5.1: URLs Persist Across Multiple Retrievals**

**Objective**: Verify that URLs don't disappear after repeated retrievals

**Steps**:

1. Use the `concept_id` from **Test 3.2** (Python AsyncIO Test - now has 2 URLs after update)
2. Call `get_concept` **3 times in a row** with the same concept_id
3. **Expected Result** (all 3 retrievals):
   - `success`: true
   - `concept.source_urls`: Array with 2 URLs
   - URLs identical across all 3 retrievals

4. **Verification**:
   - Compare all 3 responses
   - Verify source_urls are identical in all 3
   - Verify URLs don't change or disappear

**Pass Criteria**: ✅ URLs remain stable across multiple retrievals

---

### **Test 5.2: URLs Survive Concept Metadata Updates**

**Objective**: Verify that URLs persist even after updating other concept fields

**Steps**:

1. Use the `concept_id` from **Test 1.2** (React Hooks Test)
2. Get current source_urls: Call `get_concept` and save the URL list
3. Update metadata: Call `update_concept` to change `topic`:
   ```json
   {
     "concept_id": "[concept_id from Test 1.2]",
     "topic": "React Framework"
   }
   ```
4. Retrieve again: Call `get_concept` with same concept_id
5. **Expected Result**:
   - Topic changed to "React Framework"
   - source_urls unchanged (still 3 URLs)

6. **Verification**:
   - Compare source_urls before and after topic update
   - All 3 URLs should be identical
   - No URLs lost or modified

**Pass Criteria**: ✅ URLs unaffected by metadata updates

---

## 📊 **TEST EXECUTION CHECKLIST**

Use this checklist to track your progress:

### Suite 1: Create Concepts with URLs

- [ ] Test 1.1: Create with single URL (official)
- [ ] Test 1.2: Create with multiple URLs (mixed)
- [ ] Test 1.3: Create without URLs (backward compat)

### Suite 2: Retrieve and Verify URLs

- [ ] Test 2.1: Retrieve concept with single URL
- [ ] Test 2.2: Retrieve concept with multiple URLs
- [ ] Test 2.3: Retrieve concept without URLs

### Suite 3: Update URLs

- [ ] Test 3.1: Add URLs to concept without URLs
- [ ] Test 3.2: Modify existing URLs
- [ ] Test 3.3: Update other fields without touching URLs

### Suite 4: Validation and Error Handling

- [ ] Test 4.1: Invalid JSON rejected
- [ ] Test 4.2: Wrong data type rejected
- [ ] Test 4.3: Missing "url" field rejected

### Suite 5: Persistence Verification

- [ ] Test 5.1: URLs persist across multiple retrievals
- [ ] Test 5.2: URLs survive metadata updates

---

## 📝 **TEST RESULTS TEMPLATE**

After completing all tests, fill out this summary:

```markdown
## Test Execution Summary

**Date**: [Date]
**Tester**: Claude Desktop
**Environment**: Knowledge MCP Server

### Results Overview

- **Total Tests**: 13
- **Passed**: [X]
- **Failed**: [X]
- **Skipped**: [X]

### Suite 1: Create Concepts with URLs

- Test 1.1: [PASS/FAIL] - Notes:
- Test 1.2: [PASS/FAIL] - Notes:
- Test 1.3: [PASS/FAIL] - Notes:

### Suite 2: Retrieve and Verify URLs

- Test 2.1: [PASS/FAIL] - Notes:
- Test 2.2: [PASS/FAIL] - Notes:
- Test 2.3: [PASS/FAIL] - Notes:

### Suite 3: Update URLs

- Test 3.1: [PASS/FAIL] - Notes:
- Test 3.2: [PASS/FAIL] - Notes:
- Test 3.3: [PASS/FAIL] - Notes:

### Suite 4: Validation and Error Handling

- Test 4.1: [PASS/FAIL] - Notes:
- Test 4.2: [PASS/FAIL] - Notes:
- Test 4.3: [PASS/FAIL] - Notes:

### Suite 5: Persistence Verification

- Test 5.1: [PASS/FAIL] - Notes:
- Test 5.2: [PASS/FAIL] - Notes:

### Issues Found

[List any issues discovered during testing]

### Recommendations

[Any recommendations for improvements]

### Overall Assessment

[PASS/FAIL] - The source_urls feature is [ready/not ready] for production.
```

---

## 🎯 **Success Criteria**

The feature is considered **READY FOR PRODUCTION** if:

✅ All 13 tests pass
✅ URLs are stored correctly in Neo4j
✅ URLs are retrieved correctly via get_concept
✅ URLs can be updated/modified
✅ URLs persist across multiple retrievals
✅ Backward compatibility maintained (concepts work without URLs)
✅ Invalid data is rejected with clear error messages
✅ No data loss or corruption during updates

---

## 🚨 **Important Notes**

1. **Save Concept IDs**: Make sure to save the concept_id returned from each create_concept call for use in later tests.

2. **JSON Format**: The source_urls parameter must be a **JSON STRING**, not a JSON object. Use proper escaping:
   - ✅ Correct: `"source_urls": "[{\"url\": \"...\"}]"`
   - ❌ Wrong: `"source_urls": [{"url": "..."}]`

3. **MCP Tool Access**: You must have the Knowledge MCP server running and accessible via MCP tools.

4. **Error Handling**: When tests fail, record the exact error message and the parameters used.

5. **Cleanup**: After testing, you may want to delete the test concepts created.

---

## 📚 **Reference: source_urls Format**

**Expected JSON Structure**:

```json
[
  {
    "url": "https://example.com", // REQUIRED
    "title": "Example Page", // OPTIONAL
    "quality_score": 0.8, // OPTIONAL (0.0 to 1.0)
    "domain_category": "in_depth" // OPTIONAL ("official", "in_depth", "authoritative")
  }
]
```

**Quality Score Guidelines**:

- `1.0`: Official documentation
- `0.8`: In-depth tutorials/guides
- `0.6`: Authoritative community sources

**Domain Categories**:

- `"official"`: Official docs (docs.python.org, react.dev)
- `"in_depth"`: Tutorial sites (realpython.com, freecodecamp.org)
- `"authoritative"`: Community sources (github.com, stackoverflow.com)

---

## ✅ **End of Test Protocol**

Good luck with testing! 🚀
