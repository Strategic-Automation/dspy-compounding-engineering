## 2024-05-23 - Optimize string replacements
**Learning:** `str.replace` is faster than `re.sub` for simple, static substring replacements.
**Action:** When replacing static substrings, prefer `str.replace` over compiling and running a regex.

## 2024-05-23 - Optimize prefix extraction
**Learning:** Using native string operations like `str.split()` and `str.isdigit()` is significantly faster than compiling and executing regex (e.g., `re.match`) for simple string prefix extraction.
**Action:** When extracting simple prefixes from strings, prefer native string methods over regex as they are more performant.
