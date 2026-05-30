## 2024-05-23 - Optimize string replacements
**Learning:** `str.replace` is faster than `re.sub` for simple, static substring replacements.
**Action:** When replacing static substrings, prefer `str.replace` over compiling and running a regex.

## 2024-06-25 - Avoid redundant external process calls
**Learning:** Repeated calls to external processes (like `git rev-parse`) in utility functions (e.g. `get_project_root`) act as a significant bottleneck because process creation overhead is extremely high compared to simple in-memory python code, especially during configuration or frequent initialization paths.
**Action:** Use `@functools.lru_cache(maxsize=1)` on static configuration accessors and utilities that rely on relatively slow/external data.
