## 2024-05-23 - Optimize string replacements
**Learning:** `str.replace` is faster than `re.sub` for simple, static substring replacements.
**Action:** When replacing static substrings, prefer `str.replace` over compiling and running a regex.
## 2024-05-23 - Optimize CLI initialization time
**Learning:** Top-level imports of heavy libraries like `dspy` and `qdrant_client` (often imported within modules like `workflows` or `utils.knowledge`) dramatically increase CLI initialization time (from ~0.4s to ~6.3s in this codebase), even for simple commands like `--help`.
**Action:** Always use lazy loading (importing inside the specific command functions) for heavy dependencies or modules that wrap them in CLI entrypoints. Ensure `import dspy` is also lazy-loaded inside configuration functions rather than at the top level.
