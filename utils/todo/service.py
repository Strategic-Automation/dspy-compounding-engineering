"""
Todo file service for managing the file-based todo tracking system.

This module provides functions for creating, updating, and managing todo files
in the todos/ directory following the compounding engineering workflow.
"""

import glob
import os
import re
from datetime import datetime
from typing import Callable, List, Optional

import frontmatter
from filelock import FileLock


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

{review_text}

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

**Effort:** {finding.get("effort", "Medium")}

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


def parse_todo(file_path: str) -> dict:
    """
    Parse a todo file and return its frontmatter and body.

    Args:
        file_path: Path to the todo file

    Returns:
        Dict containing 'frontmatter' (dict) and 'body' (str)
    """
    with open(file_path, "r") as f:
        post = frontmatter.load(f)

    return {"frontmatter": post.metadata, "body": post.content}


def serialize_todo(frontmatter_dict: dict, body: str) -> str:
    """
    Serialize frontmatter and body back into a string.

    Args:
        frontmatter_dict: Dictionary of YAML frontmatter
        body: Content body

    Returns:
        String representation of the file
    """
    # Use frontmatter.dumps but ensure it uses the format we want
    # frontmatter.dumps can sometimes be finicky with formatting, so we might want
    # to do it manually to preserve style if needed, but let's try standard first.
    post = frontmatter.Post(body, **frontmatter_dict)
    return frontmatter.dumps(post)


def atomic_update_todo(file_path: str, update_fn: Callable[[dict, str], tuple[dict, str]]) -> bool:
    """
    Atomically update a todo file using a file lock.

    Args:
        file_path: Path to the todo file
        update_fn: Function that takes (frontmatter, body) and returns (new_frontmatter, new_body)

    Returns:
        True if successful, False otherwise
    """
    lock_path = f"{file_path}.lock"
    lock = FileLock(lock_path, timeout=10)

    try:
        with lock:
            if not os.path.exists(file_path):
                return False

            parsed = parse_todo(file_path)
            new_frontmatter, new_body = update_fn(parsed["frontmatter"], parsed["body"])
            new_content = serialize_todo(new_frontmatter, new_body)

            # Write to temp file first
            tmp_path = f"{file_path}.tmp"
            with open(tmp_path, "w") as f:
                f.write(new_content)

            # Atomic rename
            os.replace(tmp_path, file_path)
            return True
    except Exception as e:
        print(f"Error updating todo {file_path}: {e}")
        if os.path.exists(f"{file_path}.tmp"):
            os.remove(f"{file_path}.tmp")
        return False
    finally:
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except OSError:
                pass


def add_work_log_entry(content: str, action: str) -> str:
    """
    Add a work log entry to the todo content.

    Args:
        content: Existing markdown content
        action: Description of the action taken

    Returns:
        Updated content with new work log entry
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_entry = f"""
### {today} - {action}

**By:** AI Agent

**Actions:**
- {action}
"""
    # Find the Work Log section
    if "## Work Log" in content:
        # Append after the header
        parts = content.split("## Work Log")
        return f"{parts[0]}## Work Log\n{log_entry}{parts[1]}"
    else:
        # Append to end if not found
        return f"{content}\n\n## Work Log\n{log_entry}"


def get_ready_todos(todos_dir: str = "todos", pattern: Optional[str] = None) -> List[str]:
    """
    Find all ready todos in the todos directory, optionally filtered by pattern.

    Args:
        todos_dir: Directory containing todos
        pattern: Optional regex pattern to filter filenames

    Returns:
        List of absolute file paths
    """
    if not os.path.exists(todos_dir):
        return []

    files = glob.glob(os.path.join(todos_dir, "*.md"))
    ready_todos = []

    for f in files:
        if pattern and not re.search(pattern, os.path.basename(f)):
            continue

        try:
            parsed = parse_todo(f)
            fm = parsed["frontmatter"]
            if fm.get("status") == "ready":
                ready_todos.append(os.path.abspath(f))
        except Exception:
            continue

    return sorted(ready_todos)


def complete_todo(
    file_path: str,
    resolution_summary: str,
    action_msg: str = "Task Completed",
    new_status: str = "completed",
    rename_to_complete: bool = True,
) -> str:
    """
    Mark a todo as complete, update its content, and optionally rename it.

    Args:
        file_path: Path to the todo file
        resolution_summary: Summary of what was done
        action_msg: Short action message for the log
        new_status: New status string (default: "completed")
        rename_to_complete: If True, rename file from *-ready-* or *-pending-* to *-complete-*

    Returns:
        Path to the (possibly new) todo file
    """
    if not os.path.exists(file_path):
        return file_path

    parsed = parse_todo(file_path)
    fm = parsed["frontmatter"]
    body = parsed["body"]

    # Update status
    fm["status"] = new_status

    # Update checkboxes if they exist (simple string replacement)
    body = body.replace("- [ ] Issue addressed", "- [x] Issue addressed")
    body = body.replace("- [ ] Tests pass", "- [x] Tests pass")
    body = body.replace("- [ ] Code reviewed", "- [x] Code reviewed")

    # Add Resolution Summary if not present
    if "## Resolution" not in body and "## Resolution Summary" not in body:
        body += f"\n\n## Resolution\n\n{resolution_summary}\n"

    # Add Work Log
    body = add_work_log_entry(body, action_msg)

    new_content = serialize_todo(fm, body)

    # Determine new path
    new_path = file_path
    if rename_to_complete:
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        # Replace status indicators in filename
        new_base = base_name.replace("-ready-", "-complete-").replace("-pending-", "-complete-")
        if new_base != base_name:
            new_path = os.path.join(dir_name, new_base)

    # Write new file
    with open(new_path, "w") as f:
        f.write(new_content)

    # Remove old file if renamed
    if new_path != file_path:
        os.remove(file_path)

    return new_path


def analyze_dependencies(todos: List[dict]) -> dict:  # noqa: C901
    """
    Analyze dependencies between todos and create execution plan.

    Args:
        todos: List of todo dictionaries with 'id' and 'frontmatter'

    Returns:
        Dict containing execution_order (batches) and mermaid_diagram
    """
    if not todos:
        return {"execution_order": [], "mermaid_diagram": ""}

    # Build dependency graph
    # Rebuild graph as "Prerequisite -> Dependent"
    # If A depends on B, then B -> A
    forward_graph = {t["id"]: set() for t in todos}
    id_to_todo = {t["id"]: t for t in todos}
    in_degree = {t["id"]: 0 for t in todos}

    for todo in todos:
        deps = todo["frontmatter"].get("dependencies", [])
        for dep in deps:
            dep_id = str(dep)
            if dep_id in id_to_todo:
                forward_graph[dep_id].add(todo["id"])
                in_degree[todo["id"]] += 1

    queue = [t["id"] for t in todos if in_degree[t["id"]] == 0]
    batches = []

    processed_count = 0
    while queue:
        current_batch = sorted(queue)
        batches.append(
            {
                "batch": len(batches) + 1,
                "todos": current_batch,
                "can_parallel": True,
            }
        )
        processed_count += len(current_batch)

        next_queue = []
        for t_id in current_batch:
            for dependent in forward_graph[t_id]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    next_queue.append(dependent)
        queue = next_queue

    if processed_count < len(todos):
        # Cycle detected or missing dependencies
        remaining = [t["id"] for t in todos if in_degree[t["id"]] > 0]
        batches.append(
            {
                "batch": len(batches) + 1,
                "todos": remaining,
                "can_parallel": False,
                "warning": "Cycle detected or missing dependencies",
            }
        )

    # Generate Mermaid diagram
    mermaid = ["flowchart TD"]
    for t_id in forward_graph:
        mermaid.append(f"  T{t_id}[Todo {t_id}]")
        for dep in forward_graph[t_id]:
            mermaid.append(f"  T{t_id} --> T{dep}")

    return {"execution_order": batches, "mermaid_diagram": "\n".join(mermaid)}
