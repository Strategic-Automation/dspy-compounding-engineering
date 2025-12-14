"""Friday Context - Conversation and file context management"""

import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Set


class ConversationContext:
    """Manages conversation history and context"""

    def __init__(self, max_messages: int = 50):
        self.messages: List[Dict[str, Any]] = []
        self.files_mentioned: Set[str] = set()
        self.files_content: Dict[str, str] = {}
        self.max_messages = max_messages
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.working_dir = os.getcwd()
        self._load_session()

    def _get_session_file(self) -> str:
        """Get path to session file"""
        friday_dir = os.path.expanduser("~/.friday")
        os.makedirs(friday_dir, exist_ok=True)
        dir_hash = hashlib.md5(self.working_dir.encode()).hexdigest()[:8]
        return os.path.join(friday_dir, f"session_{dir_hash}.json")

    def _load_session(self):
        """Load previous session if exists"""
        session_file = self._get_session_file()
        if os.path.exists(session_file):
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                    self.messages = data.get("messages", [])[-self.max_messages:]
                    self.files_mentioned = set(data.get("files_mentioned", []))
            except Exception:
                pass

    def save(self):
        """Save session to file"""
        session_file = self._get_session_file()
        try:
            with open(session_file, "w") as f:
                json.dump({
                    "messages": self.messages[-self.max_messages:],
                    "files_mentioned": list(self.files_mentioned),
                    "working_dir": self.working_dir,
                    "updated_at": datetime.now().isoformat(),
                }, f, indent=2)
        except Exception:
            pass

    def add_user_message(self, content: str):
        """Add a user message to history"""
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self._extract_file_mentions(content)
        self._trim_messages()

    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict]] = None):
        """Add an assistant message to history"""
        msg = {
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)
        self._trim_messages()

    def add_tool_result(self, tool_name: str, result: str):
        """Add a tool result to history"""
        self.messages.append({
            "role": "tool",
            "tool": tool_name,
            "content": result[:2000],
            "timestamp": datetime.now().isoformat(),
        })
        self._trim_messages()

    def _extract_file_mentions(self, content: str):
        """Extract file paths mentioned in content"""
        import re
        patterns = [
            r'`([^`]+\.[a-zA-Z0-9]+)`',
            r'"([^"]+\.[a-zA-Z0-9]+)"',
            r"'([^']+\.[a-zA-Z0-9]+)'",
            r'\b(\S+\.[a-zA-Z0-9]+)\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if os.path.exists(match):
                    self.files_mentioned.add(match)

    def add_file_context(self, filepath: str, content: str):
        """Add file content to context"""
        self.files_mentioned.add(filepath)
        self.files_content[filepath] = content[:10000]

    def get_file_context(self, filepath: str) -> Optional[str]:
        """Get cached file content"""
        return self.files_content.get(filepath)

    def _trim_messages(self):
        """Trim messages to max limit"""
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def clear(self):
        """Clear conversation history"""
        self.messages = []
        self.files_mentioned = set()
        self.files_content = {}

    def compact(self):
        """Compact conversation history by summarizing old messages"""
        if len(self.messages) < 20:
            return
        
        old_messages = self.messages[:-10]
        recent_messages = self.messages[-10:]
        
        summary_parts = []
        for msg in old_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")[:100]
            if role == "user":
                summary_parts.append(f"User asked about: {content}")
            elif role == "assistant":
                summary_parts.append(f"Assistant helped with: {content}")
        
        summary = {
            "role": "system",
            "content": "Previous conversation summary:\n" + "\n".join(summary_parts[-5:]),
            "timestamp": datetime.now().isoformat(),
        }
        
        self.messages = [summary] + recent_messages

    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """Get messages formatted for LLM"""
        formatted = []
        
        for msg in self.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "tool":
                tool_name = msg.get("tool", "unknown")
                formatted.append({
                    "role": "user",
                    "content": f"[Tool Result - {tool_name}]:\n{content}"
                })
            else:
                formatted.append({
                    "role": "user" if role == "user" else "assistant",
                    "content": content
                })
        
        return formatted

    def get_system_context(self) -> str:
        """Get system context including mentioned files"""
        context_parts = [
            f"Working directory: {self.working_dir}",
        ]
        
        if self.files_mentioned:
            context_parts.append(f"Files mentioned in conversation: {', '.join(list(self.files_mentioned)[:10])}")
        
        return "\n".join(context_parts)
