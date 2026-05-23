## 2024-05-24 - CLI Markdown Rendering
**Learning:** Pure CLI applications utilizing `rich` library can still benefit from rich markdown rendering to make diagnostic outputs easier to read.
**Action:** When working on CLI apps built with `rich`, ensure strings containing markdown elements (e.g. lists, bold text) are wrapped with `Markdown()` before passing them to display elements like `Panel()`.
