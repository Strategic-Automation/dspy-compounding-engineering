## 2024-05-23 - Optimize string replacements
**Learning:** `str.replace` is faster than `re.sub` for simple, static substring replacements.
**Action:** When replacing static substrings, prefer `str.replace` over compiling and running a regex.
## 2024-05-24 - CLI Startup Time
**Learning:** Top-level imports of heavy modules like `dspy` in entry points significantly increase startup time. Using lazy loading for these imports reduces CLI boot time by ~80% (from ~6.4s to ~0.48s in this case) while maintaining correct test execution with dependency patches.
**Action:** When adding CLI commands or updating main entry points, always prefer lazy importing for heavyweight packages (like LLM/ML dependencies) inside the relevant command functions or use lazy loaders.
