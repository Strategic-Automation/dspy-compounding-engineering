"""Friday Theme - Visual styling for the CLI"""

from rich.theme import Theme
from prompt_toolkit.styles import Style as PTStyle

FRIDAY_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green",
    "user": "bold cyan",
    "assistant": "bold green",
    "tool": "bold yellow",
    "tool.name": "yellow",
    "tool.output": "dim",
    "code": "white on grey23",
    "path": "cyan underline",
    "command": "bold magenta",
    "thinking": "dim italic",
    "highlight": "bold white",
})

def get_prompt_style() -> PTStyle:
    """Get prompt_toolkit style for input"""
    return PTStyle.from_dict({
        '': '#ffffff',
        'prompt': '#00aaff bold',
        'prompt.path': '#00aaff',
        'prompt.arrow': '#00ff00 bold',
        'completion-menu.completion': 'bg:#333333 #ffffff',
        'completion-menu.completion.current': 'bg:#00aaff #000000',
        'scrollbar.background': 'bg:#333333',
        'scrollbar.button': 'bg:#666666',
    })


SPINNER_STYLES = [
    "dots",
    "dots2", 
    "dots3",
    "line",
    "arc",
    "bouncingBar",
]

ASCII_ART = {
    "friday": r"""
  _____ ____  ___ ____    _ __   __
 |  ___|  _ \|_ _|  _ \  / \\ \ / /
 | |_  | |_) || || | | |/ _ \\ V / 
 |  _| |  _ < | || |_| / ___ \| |  
 |_|   |_| \_\___|____/_/   \_\_|  
""",
    "thinking": "🤔",
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    "tool": "🔧",
    "file": "📄",
    "folder": "📁",
    "git": "🔀",
    "search": "🔍",
    "edit": "✏️",
    "run": "▶",
}

FILE_ICONS = {
    ".py": "🐍",
    ".js": "📜",
    ".ts": "📘",
    ".tsx": "⚛️",
    ".jsx": "⚛️",
    ".json": "📋",
    ".yaml": "📋",
    ".yml": "📋",
    ".md": "📝",
    ".txt": "📄",
    ".sh": "🔧",
    ".bash": "🔧",
    ".zsh": "🔧",
    ".css": "🎨",
    ".html": "🌐",
    ".sql": "🗃️",
    ".rs": "🦀",
    ".go": "🐹",
    ".rb": "💎",
    ".java": "☕",
    ".c": "⚙️",
    ".cpp": "⚙️",
    ".h": "⚙️",
}

def get_file_icon(filename: str) -> str:
    """Get icon for a file based on extension"""
    ext = "." + filename.split(".")[-1] if "." in filename else ""
    return FILE_ICONS.get(ext, "📄")
