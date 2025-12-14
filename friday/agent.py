"""Friday Agent - The AI brain powering Friday CLI"""

import os
import re
import json
from typing import List, Dict, Any, Generator

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text
from rich.syntax import Syntax

from friday.tools import ToolExecutor
from friday.context import ConversationContext
from friday.theme import ASCII_ART


class FridayAgent:
    """AI agent that processes user requests and executes actions"""

    SYSTEM_PROMPT = """You are Friday, an AI coding assistant. You help developers with software engineering tasks.

You have access to these tools:
- read_file(filepath, start_line=0, end_line=None): Read file contents
- write_file(filepath, content): Create or overwrite a file
- edit_file(filepath, old_text, new_text): Edit a file by replacing text
- list_dir(path=".", pattern="*", show_hidden=False): List directory contents
- search(pattern, path=".", file_pattern="*"): Search for text in files
- glob(patterns, path="."): Find files matching patterns
- execute(command): Run a shell command
- git_status(): Get git status
- git_diff(target="HEAD"): Get git diff
- git_log(count=10): Get git commit history

When responding:
1. Think step by step about what the user needs
2. Use tools when you need to read, modify, or search code
3. Show your work - explain what you're doing
4. Be concise but thorough
5. Format code with proper syntax highlighting
6. If you make changes, summarize what you did

To use a tool, output a JSON block like this:
```tool
{"name": "read_file", "args": {"filepath": "src/main.py"}}
```

You can use multiple tools in sequence. After each tool result, continue your response.

Current working directory: {cwd}
{context}
"""

    def __init__(self, console: Console, tools: ToolExecutor, context: ConversationContext):
        self.console = console
        self.tools = tools
        self.context = context
        self._init_llm()

    def _init_llm(self):
        """Initialize the LLM client"""
        try:
            import openai
            from dotenv import load_dotenv
            load_dotenv()
            
            provider = os.getenv("DSPY_LM_PROVIDER", "openai")
            
            if provider == "openai":
                self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.model = os.getenv("DSPY_LM_MODEL", "gpt-4o")
            elif provider == "anthropic":
                import anthropic
                self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                self.model = os.getenv("DSPY_LM_MODEL", "claude-3-5-sonnet-20241022")
                self.provider = "anthropic"
                return
            elif provider == "openrouter":
                self.client = openai.OpenAI(
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    base_url="https://openrouter.ai/api/v1"
                )
                self.model = os.getenv("DSPY_LM_MODEL", "anthropic/claude-3.5-sonnet")
            else:
                self.client = None
                self.model = None
                self.console.print("[yellow]Warning: No LLM configured. Set OPENAI_API_KEY or configure provider.[/]")
                return
            
            self.provider = "openai"
            
        except Exception as e:
            self.client = None
            self.model = None
            self.console.print(f"[yellow]Warning: Could not initialize LLM: {e}[/]")

    def _get_system_prompt(self) -> str:
        """Build the system prompt with current context"""
        return self.SYSTEM_PROMPT.format(
            cwd=os.getcwd(),
            context=self.context.get_system_context()
        )

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse tool calls from assistant response"""
        tool_calls = []
        
        pattern = r"```tool\s*\n(.*?)\n```"
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                tool_data = json.loads(match.strip())
                tool_calls.append(tool_data)
            except json.JSONDecodeError:
                continue
        
        return tool_calls

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a tool and return the result"""
        tool_map = {
            "read_file": lambda: self.tools.read_file(
                args.get("filepath", ""),
                args.get("start_line", 0),
                args.get("end_line")
            ),
            "write_file": lambda: self.tools.write_file(
                args.get("filepath", ""),
                args.get("content", "")
            ),
            "edit_file": lambda: self.tools.edit_file(
                args.get("filepath", ""),
                args.get("old_text", ""),
                args.get("new_text", "")
            ),
            "list_dir": lambda: self.tools.list_directory(
                args.get("path", "."),
                args.get("pattern", "*"),
                args.get("show_hidden", False)
            ),
            "search": lambda: self.tools.search_files(
                args.get("pattern", ""),
                args.get("path", "."),
                args.get("file_pattern", "*")
            ),
            "glob": lambda: self.tools.glob_files(
                args.get("patterns", []),
                args.get("path", ".")
            ),
            "execute": lambda: self.tools.execute_command(
                args.get("command", "")
            ),
            "git_status": lambda: self.tools.git_status(),
            "git_diff": lambda: self.tools.git_diff(args.get("target", "HEAD")),
            "git_log": lambda: self.tools.git_log(args.get("count", 10)),
        }
        
        if tool_name not in tool_map:
            return f"Unknown tool: {tool_name}"
        
        self.console.print(f"\n[bold yellow]{ASCII_ART['tool']} Using tool:[/] [yellow]{tool_name}[/]")
        if args:
            args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
            self.console.print(f"[dim]  args: {args_str}[/]")
        
        try:
            success, result = tool_map[tool_name]()
            
            if success:
                return result
            else:
                self.console.print(f"[red]Tool error: {result}[/]")
                return f"Error: {result}"
                
        except Exception as e:
            self.console.print(f"[red]Tool exception: {e}[/]")
            return f"Error: {e}"

    def _stream_response(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """Stream response from LLM"""
        if not self.client:
            yield "I'm not properly configured. Please set up your LLM provider (OPENAI_API_KEY, etc.)"
            return
        
        try:
            if hasattr(self, 'provider') and self.provider == "anthropic":
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=4096,
                    system=self._get_system_prompt(),
                    messages=messages
                ) as stream:
                    for text in stream.text_stream:
                        yield text
            else:
                full_messages = [{"role": "system", "content": self._get_system_prompt()}] + messages
                
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,
                    stream=True,
                    max_tokens=4096,
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
        except Exception as e:
            yield f"\n\n[Error communicating with LLM: {e}]"

    def _render_response(self, content: str):
        """Render assistant response with proper formatting"""
        code_pattern = r"```(\w*)\n(.*?)```"
        
        parts = re.split(code_pattern, content, flags=re.DOTALL)
        
        i = 0
        while i < len(parts):
            if i + 2 < len(parts) and parts[i+1] and parts[i+2]:
                if parts[i].strip():
                    self.console.print(Markdown(parts[i]))
                
                lang = parts[i+1] or "text"
                code = parts[i+2]
                
                if lang != "tool":
                    syntax = Syntax(code.strip(), lang, theme="monokai", 
                                   line_numbers=True, word_wrap=True)
                    self.console.print(Panel(syntax, border_style="dim"))
                
                i += 3
            else:
                if parts[i].strip():
                    clean_text = re.sub(r"```tool\n.*?\n```", "", parts[i], flags=re.DOTALL)
                    if clean_text.strip():
                        self.console.print(Markdown(clean_text))
                i += 1

    def process_message(self, user_input: str):
        """Process a user message and generate response"""
        self.context.add_user_message(user_input)
        
        messages = self.context.get_context_for_llm()
        
        self.console.print()
        
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            self.console.print("[bold green]Friday[/] ", end="")
            if iteration > 1:
                self.console.print("[dim](continuing...)[/]")
            
            full_response = ""
            
            with Live(Spinner("dots", text="Thinking...", style="cyan"), 
                      console=self.console, refresh_per_second=10) as live:
                
                buffer = ""
                for chunk in self._stream_response(messages):
                    full_response += chunk
                    buffer += chunk
                    
                    if len(buffer) > 50 or chunk.endswith(('\n', '.', '!', '?')):
                        live.update(Text(buffer[-100:], style="dim"))
            
            self.console.print()
            
            tool_calls = self._parse_tool_calls(full_response)
            
            response_without_tools = re.sub(r"```tool\n.*?\n```", "", full_response, flags=re.DOTALL)
            if response_without_tools.strip():
                self._render_response(response_without_tools)
            
            if not tool_calls:
                self.context.add_assistant_message(full_response)
                break
            
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                
                result = self._execute_tool(tool_name, tool_args)
                tool_results.append(f"[{tool_name}]: {result[:1000]}")
                self.context.add_tool_result(tool_name, result)
            
            messages = self.context.get_context_for_llm()
            
            self.context.add_assistant_message(full_response, tool_calls)
        
        self.console.print()
        self.context.save()
