## 2024-05-23 - Optimize string replacements
**Learning:** `str.replace` is faster than `re.sub` for simple, static substring replacements.
**Action:** When replacing static substrings, prefer `str.replace` over compiling and running a regex.

## 2024-05-31 - Optimize Scrubber
**Learning:** `re.compile` reduces regex parsing overhead for multiple iterations, which applies naturally to data scrubbing on large sets of strings. However, when combined dynamically inside of a tight loop, avoiding inner closure creation helps even more.
**Action:** Always prefer `re.compile` in an initialization block (`__init__`) and iterate through `compiled_pattern.sub()` instead of `re.sub(pattern, ...)` to improve string processing bounds over thousands of iterations.
