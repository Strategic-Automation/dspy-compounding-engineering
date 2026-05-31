## 2024-05-15 - Micro-UX Observation
**Learning:** Found no package.json, which means this isn't a Node/frontend project, but a pure Python CLI. UX enhancements here should focus on CLI interactions, output formatting, or accessible documentation output.
**Action:** Always check the project type before assuming frontend tasks.
## 2024-05-15 - Command output enhancement
**Learning:** Found that CLI output via `SystemLogger.info` only prints to console if `to_cli=True`, otherwise it only logs to file. This makes some commands feel unresponsive, like it is hanging, to the user.
**Action:** Enhance CLI UX by changing the rich console output using rich spinners for long operations.
## 2024-05-31 - Add Spinner to LLM operations
**Learning:** Found that long-running and async LLM operations, such as `compress_ai_md` in `utils/knowledge/docs.py`, cause the CLI to hang without any visual feedback. This results in poor UX, making the user wonder if the command is stuck.
**Action:** Always wrap long-running LLM or slow network operations with `logger.status` (instead of `console.status` per instructions) so that users see a spinner.
