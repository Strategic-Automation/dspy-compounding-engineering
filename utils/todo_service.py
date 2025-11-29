"""
Todo file service for managing the file-based todo tracking system.

This module provides functions for creating, updating, and managing todo files
in the todos/ directory following the compounding engineering workflow.
"""

import os
import re
import glob
from datetime import datetime
from typing import Optional


def get_next_issue_id(todos_dir: str = "todos") -> int:
    """Get the next available issue ID by scanning existing todos."""
    if not os.path.exists(todos_dir):
        os.makedirs(todos_dir, exist_ok=True)
        return 1

    existing_files = glob.glob(os.path.join(todos_dir, "*.md"))
    if not existing_files:
        return 1

    max_id = 0
    for filepath in existing_files:
        filename = os.path.basename(filepath)
        match = re.match(r"^(\d+)-", filename)
        if match:
            max_id = max(max_id, int(match.group(1)))

    return max_id + 1


def sanitize_description(description: str) -> str:
    """Convert a description to kebab-case for filename."""
    # Lowercase and replace spaces/special chars with hyphens
    slug = description.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)  # Collapse multiple hyphens
    slug = slug.strip("-")
    return slug[:50]  # Limit length


def create_finding_todo(
    finding: dict,
    todos_dir: str = "todos",
    issue_id: Optional[int] = None,
) -> str:
    """
    Create a pending todo file from a review finding.

    Args:
        finding: Dict with keys: agent, review, severity (p1/p2/p3), 
                 category, location, description, solution, effort
        todos_dir: Directory to store todos
        issue_id: Optional specific issue ID, otherwise auto-generated

    Returns:
        Path to the created todo file
    """
    os.makedirs(todos_dir, exist_ok=True)

    if issue_id is None:
        issue_id = get_next_issue_id(todos_dir)

    # Extract finding details with defaults
    agent = finding.get("agent", "Unknown Agent")
    review_text = finding.get("review", "No details provided")
    severity = finding.get("severity", "p2")
    category = finding.get("category", "code-review")
    title = finding.get("title", f"Finding from {agent}")
    
    # Create filename
    desc_slug = sanitize_description(title)
    filename = f"{issue_id:03d}-pending-{severity}-{desc_slug}.md"
    filepath = os.path.join(todos_dir, filename)

    # Build tags list
    tags = ["code-review", category.lower().replace(" ", "-")]
    if severity == "p1":
        tags.append("critical")

    today = datetime.now().strftime("%Y-%m-%d")

    content = f"""---
status: pending
priority: {severity}
issue_id: "{issue_id:03d}"
tags: [{", ".join(tags)}]
dependencies: []
---

# {title}

## Problem Statement

Finding from **{agent}** during code review.

{review_text[:2000] if len(review_text) > 2000 else review_text}

## Findings

- **Source:** {agent}
- **Category:** {category}
- **Severity:** {severity.upper()}

## Proposed Solutions

### Option 1: Address Finding

**Approach:** Review and implement the suggested fix from the code review.

**Pros:**
- Addresses the identified issue
- Improves code quality

**Cons:**
- Requires investigation time

**Effort:** {finding.get('effort', 'Medium')}

**Risk:** Low

## Recommended Action

*To be filled during triage.*

## Acceptance Criteria

- [ ] Issue addressed
- [ ] Tests pass
- [ ] Code reviewed

## Work Log

### {today} - Created from Code Review

**By:** Review Agent ({agent})

**Actions:**
- Finding identified during automated code review
- Todo created for triage

**Learnings:**
- Pending triage decision

## Notes

Source: Automated code review
"""

    with open(filepath, "w") as f:
        f.write(content)

    return filepath

