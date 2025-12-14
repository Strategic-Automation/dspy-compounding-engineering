#!/usr/bin/env python3
"""Test script to demonstrate Friday CLI UI improvements"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from friday.theme import THEMES, ASCII_ART, get_rich_theme

def test_themes():
    """Test all theme profiles"""
    for theme_name in ["dark", "light", "hc"]:
        console = Console(theme=get_rich_theme(theme_name), force_terminal=True)
        
        console.print(f"\n{'='*60}")
        console.print(f"[header]Testing Theme: {theme_name.upper()}[/]")
        console.print(f"{'='*60}\n")
        
        # Test ASCII art
        console.print(f"[bold cyan]{ASCII_ART['friday']}[/]")
        
        # Test panel
        body = "\n".join([
            "[header]FRIDAY[/] [muted]v0.1.0[/]",
            "[subheader]AI-Powered Coding Assistant[/]",
            "",
            "[muted]💡 Test theme colors and formatting[/]",
            "",
            "[command]/help[/]   [muted]Show available commands[/]",
            "[command]/clear[/]  [muted]Clear conversation[/]",
            "[command]/exit[/]   [muted]Exit Friday[/]",
        ])
        console.print(Panel.fit(body, border_style="accent", padding=(0, 1)))
        
        # Test status messages
        console.print(f"\n[success]✓ Success message[/]")
        console.print(f"[error]✗ Error message[/]")
        console.print(f"[warning]⚠ Warning message[/]")
        console.print(f"[info]ℹ Info message[/]")
        
        # Test table
        table = Table(title="[header]Sample Table[/]", border_style="accent", show_header=True, header_style="bold subheader")
        table.add_column("Item", style="subheader", width=20)
        table.add_column("Value", style="white")
        
        table.add_row("📁 Working Directory", "[path]/home/user/project[/]")
        table.add_row("🔀 Git Branch", "[accent]main[/]")
        table.add_row("💬 Conversation Turns", "[info]15[/]")
        
        console.print(table)
        
        # Test prompt simulation
        console.print(f"\n[prompt.path]project[/] [info]#5[/] [prompt.arrow]›[/] [muted]user input here...[/]")
        
        # Test separator
        console.print(f"[separator]{'─' * 60}[/]")

def test_icons():
    """Test all icons"""
    console = Console(theme=get_rich_theme("dark"), force_terminal=True)
    
    console.print("\n[header]Icon Set[/]")
    for key, icon in ASCII_ART.items():
        if key not in ["friday", "friday_compact"]:
            console.print(f"  {icon} [muted]{key}[/]")

if __name__ == "__main__":
    test_themes()
    test_icons()
    print("\n✓ UI Test Complete!\n")
