## 2024-05-23 - Optimize string replacements
**Learning:** `str.replace` is faster than `re.sub` for simple, static substring replacements.
**Action:** When replacing static substrings, prefer `str.replace` over compiling and running a regex.

## 2024-05-26 - Lazy Load Heavy Libraries for Fast CLI
**Learning:** Top-level imports of heavy ML libraries (like `dspy`, `litellm`, `qdrant_client`) in CLI apps cause massive latency on startup (e.g., 14s+ delay). This prevents users from even seeing `--help` quickly.
**Action:** Move heavy imports out of the top-level scope (e.g., in `cli.py` or global setup files like `config.py`) and into the specific command functions that need them. This dramatically speeds up CLI response time.
