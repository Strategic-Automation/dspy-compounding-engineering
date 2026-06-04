## 2024-05-23 - Optimize string replacements
**Learning:** `str.replace` is faster than `re.sub` for simple, static substring replacements.
**Action:** When replacing static substrings, prefer `str.replace` over compiling and running a regex.

## 2024-06-04 - Cache expensive subprocess calls
**Learning:** Utilities invoking slow operations (like `git rev-parse` via `subprocess`) inside often-used functions like `get_project_root()` can become invisible performance bottlenecks (~9ms overhead per call).
**Action:** When a static directory path or global property relies on slow `subprocess` operations, wrap it in `@functools.lru_cache(maxsize=1)`. Remember to invoke `.cache_clear()` inside tests that mock related environmental or structural variables.
