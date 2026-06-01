## 2025-02-23 - Replaced MD5 with SHA-256 for Hashing
**Vulnerability:** Use of insecure MD5 hashing algorithm for cache keys in `utils/knowledge/compression.py`, `utils/knowledge/docs.py`, and `utils/token/counter.py`.
**Learning:** While MD5 was used for caching and not password hashing, its presence triggers SAST tools and poses collision vulnerabilities. Upgrading to SHA-256 prevents static analysis warnings and complies with modern security standards without sacrificing performance significantly.
**Prevention:** Always use secure hashing algorithms (like SHA-256 or better) even for non-cryptographic purposes (like cache keys) to avoid collision risks and pass static security analysis checks.

## 2025-02-23 - Enforce Safe Subprocess Wrapper Usage
**Vulnerability:** Use of direct `subprocess.run` calls (e.g., in `workflows/review.py`) instead of the custom `run_safe_command` wrapper (`utils.io.safe`), bypassing the executable allowlist and `shell=True` prevention mechanisms.
**Learning:** Security wrappers like `run_safe_command` are only effective if used universally. Direct use of lower-level execution primitives can silently circumvent established security controls, creating command execution and injection risks.
**Prevention:** Consistently audit and refactor all command execution logic to route through centralized safe wrappers. Prohibit direct use of modules like `subprocess` or `os.system` via linting rules or code review policies.

## 2025-02-23 - Prevent Arbitrary Code Execution during Code Generation
**Vulnerability:** Use of `compile(..., "exec")` on untrusted AI-generated string inputs in `workflows/generate_agent.py` for syntax validation.
**Learning:** `compile` with `"exec"` can generate executable bytecode, introducing an arbitrary code execution risk or a Denial of Service (DoS) vulnerability via deeply nested or complex ASTs crafted by a compromised or malicious LLM.
**Prevention:** Always use `ast.parse()` when validating the syntax of untrusted Python code strings to parse them safely into abstract syntax trees without compiling them into executable bytecode.
