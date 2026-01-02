# Planning Features

The `plan` command helps you transform high-level feature descriptions into detailed, actionable implementation plans. It uses AI to analyze your repository, check for existing patterns, and create a comprehensive roadmap for your changes.

## Usage

```bash
compounding plan "FEATURE_DESCRIPTION"
```

### Arguments

- `FEATURE_DESCRIPTION`: A natural language description of the feature you want to implement. Be as specific or as high-level as you like.

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
