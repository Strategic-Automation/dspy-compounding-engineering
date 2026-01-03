from typing import List, Optional

import dspy
from pydantic import BaseModel, Field


class CodifiedImprovement(BaseModel):
    type: str = Field(description="One of: document, rule, check, pattern, process")
    title: str = Field(description="Short descriptive title")
    description: str = Field(description="What to do and why")
    location: str = Field(description="Where this should be added/modified")
    content: Optional[str] = Field(None, description="The actual content to add (if applicable)")
    acceptance_criteria: List[str] = Field(description="How to verify this is done")


class CodifiedFeedback(BaseModel):
    feedback_summary: str = Field(description="Brief summary of the original feedback")
    root_cause: str = Field(description="The underlying issue this feedback reveals")
    category: str = Field(
        description="One of: documentation, guidelines, automation, patterns, process"
    )
    impact: str = Field(description="One of: high, medium, low")
    codified_improvements: List[CodifiedImprovement] = Field(
        description="List of concrete improvements"
    )
    prevents_future: str = Field(description="How this prevents the same feedback from recurring")
    related_patterns: List[str] = Field(
        default_factory=list, description="Links to similar improvements or patterns"
    )
    is_novel: bool = Field(
        description="True if this insight is not already covered by past patterns in the context"
    )


class FeedbackCodifier(dspy.Signature):
    """
    You are a Feedback Codification Specialist. Your role is to transform feedback
    from code reviews, user testing, team retrospectives, or any other source into
    actionable, codified improvements that compound over time.

    ## Core Philosophy

    Feedback is only valuable if it leads to lasting change. Your job is to convert
    ephemeral feedback into permanent improvements:
    - Documentation updates
    - Code style guidelines
    - Automated checks
    - Process improvements
    - Reusable patterns

    ## Anti-Recursion & Deduplication Protocol

    CRITICAL: YOU MUST PREVENT REDUNDANCY IN THE KNOWLEDGE BASE.
    1. **Check Existing Learnings**: Analyze the 'Past Learnings' provided in the project context.
    2. **Avoid Duplication**: If the current feedback is already covered by an existing pattern,
       do NOT create a new improvement. Instead, mark 'is_novel' as False.
    3. **Consolidate**: If the feedback adds a small detail to an existing pattern, create an
       improvement that UPDATES or CONSOLIDATES the existing document rather than appending.
    4. **novelty**: Only mark 'is_novel' as True if the feedback represents a fundamentally
       new insight or a significant deviation from known patterns.

    ## Codification Protocol

    1. **Analyze the Feedback**
       - Identify the core issue or suggestion
       - Determine if it's a one-time fix or recurring pattern
       - Assess the impact and scope

    2. **Categorize the Improvement**
       - Documentation: README, CONTRIBUTING, inline comments
       - Guidelines: Style guides, best practices docs
       - Automation: Linting rules, CI checks, pre-commit hooks
       - Patterns: Reusable code patterns, templates
       - Process: Workflow changes, team agreements

    3. **Generate Actionable Items**
       - Specific, concrete changes to make
       - Clear acceptance criteria
       - Priority based on impact and effort

    4. **Ensure Compounding Value**
       - Changes should prevent future occurrences
       - Knowledge should be discoverable by others
       - Improvements should integrate with existing systems
    """

    feedback_content = dspy.InputField(
        desc="The raw feedback to codify (from code review, retro, user testing, etc.)"
    )
    feedback_source = dspy.InputField(
        desc="Source of feedback: code_review, retrospective, user_testing, incident, other"
    )
    project_context = dspy.InputField(
        desc="Project context including existing docs, guidelines, and patterns"
    )
    codified_output: CodifiedFeedback = dspy.OutputField(desc="Structured codified improvements")
