# Planning Features

The `plan` command helps you transform high-level feature descriptions into detailed, actionable implementation plans. It uses AI to analyze your repository, check for existing patterns, and create a comprehensive roadmap for your changes.

## Usage

```bash
compounding plan "FEATURE_DESCRIPTION"
```

- `FEATURE_DESCRIPTION`: A natural language description, a GitHub issue ID (e.g., `30` or `#30`), or a full GitHub issue URL.

## Planning from GitHub Issues

The `plan` command can directly ingest GitHub issues to jumpstart the planning process.

### By Issue ID
```bash
compounding plan 30
```

### By Issue URL
```bash
compounding plan https://github.com/user/repo/issues/30
```

When an issue is provided:
1.  **Issue Fetching**: The tool uses the `gh` CLI to fetch the issue title and body.
2.  **Context Building**: The issue content is used as the primary feature description for the planning agents.
3.  **Automatic Naming**: The resulting plan file is named based on the issue title (e.g., `plans/p2-add-uv-based-installer.md`).

## Example

```bash
compounding plan "Add a new user settings page with dark mode toggle and email notification preferences"
```

## How It Works

1.  **Repository Research**: The AI explores your codebase to understand existing patterns (e.g., how settings are currently stored, how UI components are built).
2.  **Architecture Analysis**: It checks for relevant architectural guidelines in the Knowledge Base.
3.  **Plan Generation**: It generates a markdown file in the `plans/` directory (e.g., `plans/add_user_settings_page.md`).
4.  **Structure**: The plan typically includes:
    -   **Context**: What is being built and why.
    -   **Proposed Changes**: File-by-file breakdown of changes.
    -   **Verification Plan**: How to test the changes.
    -   **Risk Assessment**: Potential pitfalls.

## Output

The command outputs the path to the generated plan file. You should review this plan file.

```markdown
# Generated Plan: plans/add_user_settings_page.md

## Goal
Implement user settings page...

## Proposed Changes
### [NEW] src/components/SettingsPage.tsx
...
```

Once you are satisfied with the plan, you can execute it using the `work` command.
