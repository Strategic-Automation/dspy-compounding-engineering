## 2024-05-23 - Optimize string replacements
**Learning:** `str.replace` is faster than `re.sub` for simple, static substring replacements.
**Action:** When replacing static substrings, prefer `str.replace` over compiling and running a regex.

## 2024-05-23 - Optimize regex compilation in frequent methods
**Learning:** Recompiling regular expressions and defining closures inside heavily-used loops or methods (like a scrubber running on every log statement) incurs a significant performance overhead (~35% in our scrubber tests).
**Action:** When a method processes static regex patterns frequently, pre-compile the patterns in `__init__` (e.g. `re.compile(pattern)`) and hoist static closures into class methods.
