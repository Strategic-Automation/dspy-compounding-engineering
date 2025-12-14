"""Friday Tools - File operations, search, and command execution"""

import os
import re
import glob
import subprocess
from typing import Optional, List, Tuple

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from friday.theme import get_file_icon, ASCII_ART


class ToolExecutor:
    """Executes tools and formats output"""

    def __init__(self, console: Console):
        self.console = console
        self.last_command_output = ""

    def read_file(self, filepath: str, start_line: int = 0, end_line: Optional[int] = None) -> Tuple[bool, str]:
        """Read a file and return its contents"""
        try:
            filepath = os.path.expanduser(filepath)
            if not os.path.exists(filepath):
                return False, f"File not found: {filepath}"
            
            if not os.path.isfile(filepath):
                return False, f"Not a file: {filepath}"
            
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            if end_line is None:
                end_line = min(start_line + 200, total_lines)
            
            selected_lines = lines[start_line:end_line]
            content = "".join(selected_lines)
            
            ext = os.path.splitext(filepath)[1].lstrip(".")
            lang_map = {
                "py": "python", "js": "javascript", "ts": "typescript",
                "tsx": "tsx", "jsx": "jsx", "json": "json", "yaml": "yaml",
                "yml": "yaml", "md": "markdown", "sh": "bash", "bash": "bash",
                "sql": "sql", "html": "html", "css": "css", "rs": "rust",
                "go": "go", "rb": "ruby", "java": "java", "c": "c", "cpp": "cpp",
            }
            lang = lang_map.get(ext, "text")
            
            icon = get_file_icon(filepath)
            header = f"{icon} {filepath}"
            if start_line > 0 or end_line < total_lines:
                header += f" (lines {start_line + 1}-{end_line} of {total_lines})"
            
            syntax = Syntax(content, lang, theme="monokai", line_numbers=True, 
                          start_line=start_line + 1, word_wrap=True)
            self.console.print(Panel(syntax, title=header, border_style="cyan"))
            
            return True, content
            
        except Exception as e:
            return False, f"Error reading file: {e}"

    def write_file(self, filepath: str, content: str) -> Tuple[bool, str]:
        """Write content to a file"""
        try:
            filepath = os.path.expanduser(filepath)
            
            dir_path = os.path.dirname(filepath)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            file_exists = os.path.exists(filepath)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            action = "Updated" if file_exists else "Created"
            self.console.print(f"[green]{ASCII_ART['success']} {action}:[/] [cyan]{filepath}[/]")
            
            return True, f"{action} {filepath}"
            
        except Exception as e:
            return False, f"Error writing file: {e}"

    def edit_file(self, filepath: str, old_text: str, new_text: str) -> Tuple[bool, str]:
        """Edit a file by replacing text"""
        try:
            filepath = os.path.expanduser(filepath)
            
            if not os.path.exists(filepath):
                return False, f"File not found: {filepath}"
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            if old_text not in content:
                return False, f"Text not found in {filepath}"
            
            occurrences = content.count(old_text)
            if occurrences > 1:
                self.console.print(f"[yellow]Warning: Found {occurrences} occurrences, replacing first one[/]")
            
            new_content = content.replace(old_text, new_text, 1)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            self.console.print(f"[green]{ASCII_ART['success']} Edited:[/] [cyan]{filepath}[/]")
            
            return True, f"Edited {filepath}"
            
        except Exception as e:
            return False, f"Error editing file: {e}"

    def list_directory(self, path: str = ".", pattern: str = "*", 
                       show_hidden: bool = False, max_depth: int = 2) -> Tuple[bool, str]:
        """List directory contents"""
        try:
            path = os.path.expanduser(path)
            
            if not os.path.exists(path):
                return False, f"Path not found: {path}"
            
            tree = Tree(f"[bold cyan]{path}[/]")
            file_count = 0
            dir_count = 0
            
            def add_to_tree(current_path: str, tree_node, depth: int = 0):
                nonlocal file_count, dir_count
                
                if depth > max_depth:
                    return
                
                try:
                    entries = sorted(os.listdir(current_path))
                except PermissionError:
                    tree_node.add("[red]Permission denied[/]")
                    return
                
                skip_dirs = {"__pycache__", ".git", "node_modules", ".venv", "venv", 
                            ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build"}
                
                for entry in entries:
                    if not show_hidden and entry.startswith("."):
                        continue
                    if entry in skip_dirs:
                        continue
                    
                    entry_path = os.path.join(current_path, entry)
                    
                    if os.path.isdir(entry_path):
                        dir_count += 1
                        subtree = tree_node.add(f"[bold blue]{entry}/[/]")
                        if depth < max_depth:
                            add_to_tree(entry_path, subtree, depth + 1)
                    else:
                        if pattern != "*" and not glob.fnmatch.fnmatch(entry, pattern):
                            continue
                        file_count += 1
                        icon = get_file_icon(entry)
                        tree_node.add(f"{icon} {entry}")
            
            add_to_tree(path, tree)
            
            self.console.print(tree)
            self.console.print(f"[dim]{dir_count} directories, {file_count} files[/]")
            
            return True, f"Listed {path}: {dir_count} dirs, {file_count} files"
            
        except Exception as e:
            return False, f"Error listing directory: {e}"

    def search_files(self, pattern: str, path: str = ".", 
                     file_pattern: str = "*", max_results: int = 50) -> Tuple[bool, str]:
        """Search for pattern in files (grep-like)"""
        try:
            path = os.path.expanduser(path)
            results = []
            
            search_pattern = re.compile(pattern, re.IGNORECASE)
            
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in {
                    "__pycache__", ".git", "node_modules", ".venv", "venv"
                }]
                
                for filename in files:
                    if file_pattern != "*" and not glob.fnmatch.fnmatch(filename, file_pattern):
                        continue
                    
                    filepath = os.path.join(root, filename)
                    
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, 1):
                                if search_pattern.search(line):
                                    results.append({
                                        "file": filepath,
                                        "line": line_num,
                                        "content": line.strip()[:100]
                                    })
                                    
                                    if len(results) >= max_results:
                                        break
                    except Exception:
                        continue
                    
                    if len(results) >= max_results:
                        break
                
                if len(results) >= max_results:
                    break
            
            if not results:
                self.console.print(f"[yellow]No matches found for pattern: {pattern}[/]")
                return True, "No matches found"
            
            table = Table(title=f"Search Results: '{pattern}'", border_style="blue")
            table.add_column("File", style="cyan", no_wrap=True)
            table.add_column("Line", style="yellow", justify="right")
            table.add_column("Content", style="white")
            
            for r in results[:30]:
                table.add_row(
                    os.path.relpath(r["file"]),
                    str(r["line"]),
                    r["content"][:60] + ("..." if len(r["content"]) > 60 else "")
                )
            
            self.console.print(table)
            
            if len(results) > 30:
                self.console.print(f"[dim]... and {len(results) - 30} more matches[/]")
            
            return True, f"Found {len(results)} matches"
            
        except Exception as e:
            return False, f"Error searching: {e}"

    def glob_files(self, patterns: List[str], path: str = ".") -> Tuple[bool, str]:
        """Find files matching glob patterns"""
        try:
            path = os.path.expanduser(path)
            all_matches = []
            
            for pattern in patterns:
                full_pattern = os.path.join(path, pattern)
                matches = glob.glob(full_pattern, recursive=True)
                all_matches.extend(matches)
            
            all_matches = sorted(set(all_matches))
            
            if not all_matches:
                self.console.print(f"[yellow]No files found matching: {patterns}[/]")
                return True, "No files found"
            
            self.console.print(f"[bold]Found {len(all_matches)} files:[/]")
            for match in all_matches[:50]:
                icon = get_file_icon(match)
                rel_path = os.path.relpath(match)
                self.console.print(f"  {icon} [cyan]{rel_path}[/]")
            
            if len(all_matches) > 50:
                self.console.print(f"[dim]... and {len(all_matches) - 50} more files[/]")
            
            return True, f"Found {len(all_matches)} files"
            
        except Exception as e:
            return False, f"Error finding files: {e}"

    def execute_command(self, command: str, timeout: int = 60) -> Tuple[bool, str]:
        """Execute a shell command"""
        try:
            dangerous_patterns = [
                r"rm\s+-rf\s+[/~]",
                r"rm\s+-rf\s+\*",
                r">\s*/dev/sd",
                r"mkfs\.",
                r"dd\s+if=",
                r":\(\)\{\s*:\|:\s*&\s*\}",
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, command):
                    return False, "Dangerous command blocked for safety"
            
            self.console.print(f"[bold magenta]$ {command}[/]")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            
            output = ""
            
            if result.stdout:
                output += result.stdout
                lines = result.stdout.strip().split('\n')
                if len(lines) > 50:
                    display = '\n'.join(lines[:25] + ['...', f'({len(lines) - 50} lines omitted)', '...'] + lines[-25:])
                else:
                    display = result.stdout
                self.console.print(display)
            
            if result.stderr:
                output += result.stderr
                self.console.print(f"[red]{result.stderr}[/]")
            
            if result.returncode != 0:
                self.console.print(f"[red]Exit code: {result.returncode}[/]")
                return False, output or f"Command failed with exit code {result.returncode}"
            
            self.last_command_output = output
            return True, output or "Command completed successfully"
            
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, f"Error executing command: {e}"

    def git_status(self) -> Tuple[bool, str]:
        """Get git status"""
        return self.execute_command("git status")

    def git_diff(self, target: str = "HEAD") -> Tuple[bool, str]:
        """Get git diff"""
        return self.execute_command(f"git diff {target}")

    def git_log(self, count: int = 10) -> Tuple[bool, str]:
        """Get git log"""
        return self.execute_command(f"git log --oneline -n {count}")
