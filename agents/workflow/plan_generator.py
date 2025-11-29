import dspy

class PlanGenerator(dspy.Signature):
    """
    Transform feature descriptions, bug reports, or improvement ideas into well-structured markdown files issues that follow project conventions and best practices.

    **Goal:** Create a plan for a new feature or bug fix.

    **Input:**
    - Feature Description
    - Research Findings (Repo, Best Practices, Framework Docs)
    - SpecFlow Analysis

    **Output:**
    A comprehensive markdown plan.

    **Structure Options:**
    - **MINIMAL (Quick Issue)**: For simple bugs/improvements.
    - **MORE (Standard Issue)**: For most features.
    - **A LOT (Comprehensive Issue)**: For major features.

    Choose the appropriate detail level based on the complexity.

    **Content Formatting:**
    - Use clear, descriptive headings (##, ###)
    - Include code examples in triple backticks
    - Use task lists (- [ ])
    - Add collapsible sections for logs
    - Apply appropriate emojis

    **Structure Template (Standard):**
    ```markdown
    # [Title]

    ## Overview
    [Description]

    ## Problem Statement / Motivation
    [Why this matters]

    ## Proposed Solution
    [High-level approach]

    ## Technical Considerations
    - Architecture impacts
    - Performance
    - Security

    ## Acceptance Criteria
    - [ ] Requirement 1
    - [ ] Requirement 2

    ## Implementation Plan
    - [ ] Task 1
    - [ ] Task 2

    ## References
    - [Links]
    ```
    """
    
    feature_description = dspy.InputField(desc="The feature description")
    research_summary = dspy.InputField(desc="Combined research findings")
    spec_flow_analysis = dspy.InputField(desc="SpecFlow analysis results")
    plan_content = dspy.OutputField(desc="The generated markdown plan")
