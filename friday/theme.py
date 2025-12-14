"""Friday Theme - Visual styling for the CLI"""

from rich.theme import Theme
from prompt_toolkit.styles import Style as PTStyle

# Theme profiles: dark (default), light, high-contrast (hc)
THEMES = {
    "dark": Theme({
        "info": "bright_cyan",
        "warning": "yellow",
        "error": "bright_red bold",
        "success": "bright_green",
        "user": "bold bright_blue",
        "assistant": "bold bright_green",
        "tool": "bold bright_yellow",
        "tool.name": "bright_yellow",
        "tool.output": "grey70",
        "code": "bright_white on grey15",
        "path": "bright_cyan underline",
        "command": "bold bright_magenta",
        "thinking": "grey70 italic",
        "highlight": "bold bright_white on grey19",
        "prompt": "bright_blue bold",
        "prompt.path": "bright_cyan",
        "prompt.arrow": "bright_green bold",
        "header": "bold bright_white",
        "subheader": "bright_cyan",
        "separator": "grey50",
        "muted": "grey50",
        "accent": "bright_magenta",
    }),
    "light": Theme({
        "info": "blue",
        "warning": "dark_orange",
        "error": "red bold",
        "success": "green4",
        "user": "bold blue",
        "assistant": "bold green4",
        "tool": "bold dark_orange",
        "tool.name": "dark_orange",
        "tool.output": "grey46",
        "code": "grey11 on grey93",
        "path": "blue underline",
        "command": "bold magenta",
        "thinking": "grey54 italic",
        "highlight": "bold black on grey85",
        "prompt": "blue bold",
        "prompt.path": "cyan", # Changed from cyan4
        "prompt.arrow": "green4 bold",
        "header": "bold black",
        "subheader": "blue",
        "separator": "grey63",
        "muted": "grey63",
        "accent": "magenta",
    }),
    "hc": Theme({
        "info": "bright_cyan",
        "warning": "bright_yellow",
        "error": "bright_red bold",
        "success": "bright_green",
        "user": "bold bright_cyan",
        "assistant": "bold bright_green",
        "tool": "bold bright_yellow",
        "tool.name": "bright_yellow",
        "tool.output": "bright_white",
        "code": "bright_white on black",
        "path": "bright_cyan underline",
        "command": "bold bright_magenta",
        "thinking": "bright_white italic",
        "highlight": "bold black on bright_white",
        "prompt": "bright_cyan bold",
        "prompt.path": "bright_blue",
        "prompt.arrow": "bright_green bold",
        "header": "bold bright_white",
        "subheader": "bright_cyan",
        "separator": "white",
        "muted": "grey70",
        "accent": "bright_magenta",
    }),
}

# Backwards compatibility default theme name
FRIDAY_THEME = THEMES["dark"]

def get_rich_theme(profile: str | None) -> Theme:
    return THEMES.get((profile or "dark").lower(), THEMES["dark"])

def get_prompt_style(profile: str | None = None) -> PTStyle:
    """Get prompt_toolkit style for input for a given theme profile"""
    p = (profile or "dark").lower()
    if p == "light":
        return PTStyle.from_dict({
            '': '#1a1a1a',
            'prompt': '#0066cc bold',
            'prompt.path': '#007acc',
            'prompt.arrow': '#16825d bold',
            'completion-menu.completion': 'bg:#f0f0f0 #1a1a1a',
            'completion-menu.completion.current': 'bg:#0066cc #ffffff bold',
            'scrollbar.background': 'bg:#e0e0e0',
            'scrollbar.button': 'bg:#999999',
            'bottom-toolbar': 'bg:#f0f0f0 #666666',
        })
    if p == "hc":
        return PTStyle.from_dict({
            '': '#ffffff',
            'prompt': 'bold #00ffff',
            'prompt.path': '#00aaff',
            'prompt.arrow': 'bold #00ff00',
            'completion-menu.completion': 'bg:#000000 #ffffff bold',
            'completion-menu.completion.current': 'bg:#00ffff #000000 bold',
            'scrollbar.background': 'bg:#000000',
            'scrollbar.button': 'bg:#aaaaaa',
            'bottom-toolbar': 'bg:#000000 #ffffff bold',
        })
    # dark default
    return PTStyle.from_dict({
        '': '#e4e4e4',
        'prompt': '#4fc3f7 bold',
        'prompt.path': '#64b5f6',
        'prompt.arrow': '#66bb6a bold',
        'completion-menu.completion': 'bg:#2a2a2a #cccccc',
        'completion-menu.completion.current': 'bg:#4fc3f7 #1a1a1a bold',
        'scrollbar.background': 'bg:#1e1e1e',
        'scrollbar.button': 'bg:#505050',
        'bottom-toolbar': 'bg:#1a1a1a #888888',
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
  ███████╗██████╗ ██╗██████╗  █████╗ ██╗   ██╗
  ██╔════╝██╔══██╗██║██╔══██╗██╔══██╗╚██╗ ██╔╝
  █████╗  ██████╔╝██║██║  ██║███████║ ╚████╔╝ 
  ██╔══╝  ██╔══██╗██║██║  ██║██╔══██║  ╚██╔╝  
  ██║     ██║  ██║██║██████╔╝██║  ██║   ██║   
  ╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   
""",
    "friday_compact": r"""
  _____ ____  ___ ____    _ __   __
 |  ___|  _ \|_ _|  _ \  / \\ \ / /
 | |_  | |_) || || | | |/ _ \\ V / 
 |  _| |  _ < | || |_| / ___ \| |  
 |_|   |_| \_\___|____/_/   \_\_|  
""",
    "thinking": "💭",
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
    "check": "✓",
    "cross": "✗",
    "arrow": "→",
    "bullet": "•",
    "prompt": "›",
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
