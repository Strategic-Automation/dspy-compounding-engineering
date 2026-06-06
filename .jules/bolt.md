## 2024-05-23 - Optimize string replacements
**Learning:** `str.replace` is faster than `re.sub` for simple, static substring replacements.
**Action:** When replacing static substrings, prefer `str.replace` over compiling and running a regex.

## 2024-05-25 - Optimize string prefix extraction
**Learning:** For extracting simple prefixes (like numeric IDs) from strings, native string methods (`str.split` and `str.isdigit`) are significantly faster than compiling and running regular expressions (`re.match`).
**Action:** When extracting or checking simple string prefixes, prefer `str.split()` over `re.match()` where appropriate.
