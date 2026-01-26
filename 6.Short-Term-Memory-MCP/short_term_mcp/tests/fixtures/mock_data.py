"""Mock data for testing complete session workflows"""

from datetime import datetime

# Realistic Research session output with 25 concepts
RESEARCH_OUTPUT = {
    "session_id": "2025-10-09",
    "learning_goal": "Learn React Hooks and State Management",
    "building_goal": "Build a Todo App with React",
    "concepts": [
        # State Management Concepts (5)
        {
            "concept_name": "useState Hook",
            "data": {
                "definition": "React Hook for adding state to functional components",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Hooks",
                "resources": ["https://react.dev/reference/react/useState"],
                "knowledge_status": "new",
                "priority": "high",
            },
        },
        {
            "concept_name": "useReducer Hook",
            "data": {
                "definition": "Hook for complex state logic with actions and reducers",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Hooks",
                "resources": ["https://react.dev/reference/react/useReducer"],
                "knowledge_status": "new",
                "priority": "medium",
            },
        },
        {
            "concept_name": "State Lifting",
            "data": {
                "definition": "Moving state up to parent components for sharing",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Component Architecture",
                "resources": ["https://react.dev/learn/sharing-state-between-components"],
                "knowledge_status": "new",
                "priority": "high",
            },
        },
        {
            "concept_name": "Controlled Components",
            "data": {
                "definition": "Form inputs controlled by React state",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Forms",
                "resources": ["https://react.dev/reference/react-dom/components/input"],
                "knowledge_status": "familiar",
                "priority": "medium",
            },
        },
        {
            "concept_name": "Derived State",
            "data": {
                "definition": "State calculated from other state values",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "State Management",
                "resources": [
                    "https://react.dev/learn/you-might-not-need-an-effect#updating-state-based-on-props-or-state"
                ],
                "knowledge_status": "new",
                "priority": "low",
            },
        },
        # Effect Concepts (5)
        {
            "concept_name": "useEffect Hook",
            "data": {
                "definition": "Hook for side effects in functional components",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Hooks",
                "resources": ["https://react.dev/reference/react/useEffect"],
                "knowledge_status": "new",
                "priority": "high",
            },
        },
        {
            "concept_name": "Effect Dependencies",
            "data": {
                "definition": "Array controlling when effects re-run",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Hooks",
                "resources": ["https://react.dev/learn/synchronizing-with-effects"],
                "knowledge_status": "new",
                "priority": "high",
            },
        },
        {
            "concept_name": "Effect Cleanup",
            "data": {
                "definition": "Cleanup functions returned from effects",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Hooks",
                "resources": [
                    "https://react.dev/learn/synchronizing-with-effects#step-3-add-cleanup-if-needed"
                ],
                "knowledge_status": "new",
                "priority": "medium",
            },
        },
        {
            "concept_name": "useLayoutEffect",
            "data": {
                "definition": "Effect that fires before browser paint",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Hooks",
                "resources": ["https://react.dev/reference/react/useLayoutEffect"],
                "knowledge_status": "new",
                "priority": "low",
            },
        },
        {
            "concept_name": "Effect Race Conditions",
            "data": {
                "definition": "Issues when async effects complete out of order",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Async Patterns",
                "resources": ["https://react.dev/learn/you-might-not-need-an-effect#fetching-data"],
                "knowledge_status": "new",
                "priority": "medium",
            },
        },
        # Performance Concepts (5)
        {
            "concept_name": "useMemo Hook",
            "data": {
                "definition": "Hook for memoizing expensive calculations",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Performance",
                "resources": ["https://react.dev/reference/react/useMemo"],
                "knowledge_status": "new",
                "priority": "medium",
            },
        },
        {
            "concept_name": "useCallback Hook",
            "data": {
                "definition": "Hook for memoizing callback functions",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Performance",
                "resources": ["https://react.dev/reference/react/useCallback"],
                "knowledge_status": "new",
                "priority": "medium",
            },
        },
        {
            "concept_name": "React.memo",
            "data": {
                "definition": "Higher-order component for preventing re-renders",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Performance",
                "resources": ["https://react.dev/reference/react/memo"],
                "knowledge_status": "familiar",
                "priority": "low",
            },
        },
        {
            "concept_name": "Virtual DOM Diffing",
            "data": {
                "definition": "React's reconciliation algorithm",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Internals",
                "resources": ["https://react.dev/learn/preserving-and-resetting-state"],
                "knowledge_status": "new",
                "priority": "low",
            },
        },
        {
            "concept_name": "Keys in Lists",
            "data": {
                "definition": "Stable identifiers for list items",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Rendering",
                "resources": [
                    "https://react.dev/learn/rendering-lists#keeping-list-items-in-order-with-key"
                ],
                "knowledge_status": "familiar",
                "priority": "high",
            },
        },
        # Context & Refs (5)
        {
            "concept_name": "useContext Hook",
            "data": {
                "definition": "Hook for consuming React context",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Hooks",
                "resources": ["https://react.dev/reference/react/useContext"],
                "knowledge_status": "new",
                "priority": "high",
            },
        },
        {
            "concept_name": "Context Provider Pattern",
            "data": {
                "definition": "Pattern for providing context values to components",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Context",
                "resources": ["https://react.dev/learn/passing-data-deeply-with-context"],
                "knowledge_status": "new",
                "priority": "medium",
            },
        },
        {
            "concept_name": "useRef Hook",
            "data": {
                "definition": "Hook for mutable references and DOM access",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Hooks",
                "resources": ["https://react.dev/reference/react/useRef"],
                "knowledge_status": "new",
                "priority": "medium",
            },
        },
        {
            "concept_name": "forwardRef",
            "data": {
                "definition": "Technique for forwarding refs to child components",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Refs",
                "resources": ["https://react.dev/reference/react/forwardRef"],
                "knowledge_status": "new",
                "priority": "low",
            },
        },
        {
            "concept_name": "useImperativeHandle",
            "data": {
                "definition": "Hook for customizing ref handle exposed to parent",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Hooks",
                "resources": ["https://react.dev/reference/react/useImperativeHandle"],
                "knowledge_status": "new",
                "priority": "low",
            },
        },
        # Custom Hooks & Patterns (5)
        {
            "concept_name": "Custom Hooks",
            "data": {
                "definition": "Reusable stateful logic extracted into hooks",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Patterns",
                "resources": ["https://react.dev/learn/reusing-logic-with-custom-hooks"],
                "knowledge_status": "new",
                "priority": "high",
            },
        },
        {
            "concept_name": "useDebugValue",
            "data": {
                "definition": "Hook for labeling custom hooks in DevTools",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Debugging",
                "resources": ["https://react.dev/reference/react/useDebugValue"],
                "knowledge_status": "new",
                "priority": "low",
            },
        },
        {
            "concept_name": "Compound Components",
            "data": {
                "definition": "Pattern for components that work together",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Patterns",
                "resources": ["https://kentcdodds.com/blog/compound-components-with-react-hooks"],
                "knowledge_status": "new",
                "priority": "medium",
            },
        },
        {
            "concept_name": "Render Props",
            "data": {
                "definition": "Pattern for sharing code using function props",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Patterns",
                "resources": ["https://react.dev/reference/react/Component#render-props"],
                "knowledge_status": "familiar",
                "priority": "low",
            },
        },
        {
            "concept_name": "Error Boundaries",
            "data": {
                "definition": "Components that catch JavaScript errors in child tree",
                "area": "Frontend",
                "topic": "React",
                "subtopic": "Error Handling",
                "resources": [
                    "https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary"
                ],
                "knowledge_status": "new",
                "priority": "medium",
            },
        },
    ],
}

# AIM session chunking output
AIM_OUTPUT = {
    "session_id": "2025-10-09",
    "chunks": [
        {
            "chunk_name": "State Hooks",
            "concept_ids": ["useState", "useReducer", "State Lifting"],
            "questions": [
                "Why do we need both useState and useReducer?",
                "When should I lift state up vs use Context?",
                "How does derived state differ from useState?",
            ],
            "priority": "high",
            "estimated_time_minutes": 30,
        },
        {
            "chunk_name": "Effect Management",
            "concept_ids": ["useEffect", "Effect Dependencies", "Effect Cleanup"],
            "questions": [
                "Why do dependencies matter for effects?",
                "When should I clean up effects?",
                "What's the difference between useEffect and useLayoutEffect?",
            ],
            "priority": "high",
            "estimated_time_minutes": 40,
        },
        {
            "chunk_name": "Performance Optimization",
            "concept_ids": ["useMemo", "useCallback", "React.memo", "Keys in Lists"],
            "questions": [
                "When should I use useMemo vs useCallback?",
                "Does React.memo always prevent re-renders?",
                "Why are keys important for list performance?",
            ],
            "priority": "medium",
            "estimated_time_minutes": 25,
        },
        {
            "chunk_name": "Context & References",
            "concept_ids": ["useContext", "Context Provider Pattern", "useRef"],
            "questions": [
                "How is Context different from prop drilling?",
                "When should I use useRef instead of useState?",
                "What are the performance implications of Context?",
            ],
            "priority": "medium",
            "estimated_time_minutes": 20,
        },
        {
            "chunk_name": "Advanced Patterns",
            "concept_ids": ["Custom Hooks", "Compound Components", "Error Boundaries"],
            "questions": [
                "What makes a good custom hook?",
                "When should I use compound components?",
                "How do error boundaries fit into error handling?",
            ],
            "priority": "low",
            "estimated_time_minutes": 35,
        },
    ],
}

# SHOOT session encoding output
SHOOT_OUTPUT = {
    "session_id": "2025-10-09",
    "encodings": [
        {
            "concept_name": "useState Hook",
            "self_explanation": "useState is like giving my component a sticky note where it can write down information it needs to remember between renders. When I call useState, I get both the current value and a function to update it. Every time I update the value, React re-renders my component with the new value.",
            "difficulty": 3,
            "analogies": [
                "Like a light switch - you have the current state (on/off) and a switch to toggle it",
                "Like a notebook with a bookmark - you read the current page and can flip to a new page",
            ],
            "examples": [
                "Counter app with increment/decrement buttons",
                "Form input tracking user's typed text",
                "Toggle for showing/hiding a modal",
            ],
            "confidence": 8,
        },
        {
            "concept_name": "useEffect Hook",
            "self_explanation": "useEffect lets me run code that has side effects - things that reach outside my component like fetching data, subscribing to events, or updating the DOM directly. It runs after React finishes rendering. The dependency array tells React which values to watch, and if they change, run the effect again.",
            "difficulty": 6,
            "analogies": [
                "Like a robot butler that automatically does tasks whenever certain conditions change",
                "Like setting up automatic bill payments that trigger when your balance changes",
            ],
            "examples": [
                "Fetching user data when component mounts",
                "Setting up a WebSocket connection and cleaning it up on unmount",
                "Updating document title based on state",
            ],
            "confidence": 7,
        },
        {
            "concept_name": "useMemo Hook",
            "self_explanation": "useMemo caches the result of an expensive calculation so it doesn't run on every render. It only recalculates when one of its dependencies changes. This is useful when I have computationally expensive operations that don't need to run unless their inputs change.",
            "difficulty": 5,
            "analogies": [
                "Like writing down the answer to a math problem so you don't have to calculate it again",
                "Like caching Google search results so subsequent searches are instant",
            ],
            "examples": [
                "Filtering/sorting a large list of items",
                "Calculating statistics from array data",
                "Formatting date/time strings",
            ],
            "confidence": 6,
        },
    ],
}

# SKIN session evaluation output
SKIN_OUTPUT = {
    "session_id": "2025-10-09",
    "evaluations": [
        {
            "concept_name": "useState Hook",
            "understanding_level": "well_understood",
            "confidence_score": 9,
            "can_explain": True,
            "can_implement": True,
            "questions_answered": [
                "Why do we need both useState and useReducer?",
                "How does derived state differ from useState?",
            ],
            "remaining_confusion": None,
            "practical_application": "Used it to build todo list state management",
        },
        {
            "concept_name": "useEffect Hook",
            "understanding_level": "partially_understood",
            "confidence_score": 7,
            "can_explain": True,
            "can_implement": True,
            "questions_answered": ["Why do dependencies matter for effects?"],
            "remaining_confusion": "Still unclear about cleanup timing with async operations",
            "practical_application": "Fetched user data on component mount",
        },
        {
            "concept_name": "useMemo Hook",
            "understanding_level": "basic_understanding",
            "confidence_score": 6,
            "can_explain": True,
            "can_implement": False,
            "questions_answered": [],
            "remaining_confusion": "Not sure when the performance benefit is worth the complexity",
            "practical_application": "Haven't used in real code yet",
        },
    ],
}

# Edge cases and error scenarios
ERROR_SCENARIOS = {
    "duplicate_concepts": [
        {"concept_name": "useState Hook", "data": {"version": 1}},
        {"concept_name": "useState Hook", "data": {"version": 2}},  # Duplicate
    ],
    "missing_session": {
        "session_id": "2025-99-99",  # Invalid session
        "concepts": [{"concept_name": "Test", "data": {}}],
    },
    "partial_pipeline": {
        # Simulates crash after AIM stage - some concepts chunked, some still identified
        "processed_count": 15,  # Only 15 of 25 concepts processed
        "unprocessed_count": 10,
    },
    "invalid_status_transition": {
        # Try to jump from identified to stored without going through intermediate stages
        "from_status": "identified",
        "to_status": "stored",
    },
}
