## 2024-05-15 - Micro-UX Observation
**Learning:** Found no package.json, which means this isn't a Node/frontend project, but a pure Python CLI. UX enhancements here should focus on CLI interactions, output formatting, or accessible documentation output.
**Action:** Always check the project type before assuming frontend tasks.
## 2024-05-15 - Command output enhancement
**Learning:** Found that CLI output via `SystemLogger.info` only prints to console if `to_cli=True`, otherwise it only logs to file. This makes some commands feel unresponsive, like it is hanging, to the user.
**Action:** Enhance CLI UX by changing the rich console output using rich spinners for long operations.
## 2024-05-15 - Spinner implementation via context managers
**Learning:** Adding spinners to long-running synchronous code in Python CLIs is best done via context managers (e.g. `with logger.status(...)`) rather than separate start/stop function calls. This naturally limits the lifetime of the spinner and prevents unhandled exceptions from leaving the spinner in an orphaned running state on the CLI.
**Action:** Always prefer `with context_manager:` for UI indicators when updating CLI scripts.
