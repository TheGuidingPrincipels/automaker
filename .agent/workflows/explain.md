---
description: Deeply analyze and explain codebase concepts covering big picture, technical details, and specific behaviors using scientific exploration and learning science principles.
---
1. **Analyze User Question & Intent**
   - The user has asked a question immediately following this command.
   - **Goal**: Provide a complete, verified, and pedagogically sound explanation.
   - **Constraint**: **NO ASSUMPTIONS**. Every claim must be backed by evidence found in the codebase or verified external documentation.

2. **Scientific Codebase Exploration (Mandatory Phase)**
   - **Map the Territory**:
     - Use `find_by_name` or `list_dir` to locate relevant files if not immediately obvious.
     - Use `view_file_outline` to understand the structure of key files.
   - **Trace the Logic**:
     - Use `grep_search` to find usage patterns of relevant functions, classes, or constants.
     - Use `view_file` to read the actual implementation details. do not rely on filenames alone.
   - **Verify External Dependencies**:
     - IF usage involves external libraries/APIs and you are not 100% sure of the version or specific behavior:
       - Use `resolve-library-id` and `query-docs` (via Context7) OR `search_web` to verify behavior.
       - *Do not guess* how a library function works.

3. **Synthesize the Explanation (Pedagogical Strategy)**
   - Structure your response using the following **Strict Template**:

   ### 1. The Big Picture (Mental Model)
   - **Goal**: Connect the user's question to the broader system architecture.
   - **Technique**: Use an **Analogy** if the concept is abstract.
   - Explain *why* this exists and *how* it relates to other major parts of the system.
   - Avoid code snippets here; focus on data flow and relationships.

   ### 2. Technical Deep Dive (The "How")
   - **Goal**: Explain the specific mechanics.
   - **Technique**: "Zoom In".
   - Walk through the execution flow step-by-step.
   - Use **Code Snippets** (referenced from your `view_file` findings) to back up your explanation.
   - Explicitly highlight *different behaviors* or *edge cases* you discovered during analysis.

   ### 3. Summary & Key Takeaways
   - Bullet points summarizing the most important facts.

4. **Self-Correction & Quality Check**
   - Did you answer the *specific* question asked?
   - Did you explain *all* technical terms used?
   - Is every code behavior mentioned actually present in the files you read? (Double-check your `view_file` outputs).

5. **Final Output**
   - Present the synthesized explanation to the user.
   - Invite follow-up questions to deepen understanding.