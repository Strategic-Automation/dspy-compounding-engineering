"""
Knowledge Base module for Compounding Engineering.

This module manages the persistent storage and retrieval of learnings,
enabling the system to improve over time by accessing past insights.
"""

import os
import json
import glob
from datetime import datetime
from typing import List, Dict, Any
from rich.console import Console

console = Console()

class KnowledgeBase:
    """
    Manages a collection of learnings stored as JSON files.
    """
    
    def __init__(self, knowledge_dir: str = ".knowledge"):
        self.knowledge_dir = knowledge_dir
        self._ensure_knowledge_dir()
        
    def _ensure_knowledge_dir(self):
        """Ensure the knowledge directory exists."""
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)
            
    def add_learning(self, learning: Dict[str, Any]) -> str:
        """
        Add a new learning item to the knowledge base.
        
        Args:
            learning: Dictionary containing learning details. 
                      Should include 'category', 'title', 'description', etc.
                      
        Returns:
            Path to the saved learning file.
        """
        # Generate ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        category = learning.get("category", "general").lower().replace(" ", "-")
        filename = f"{timestamp}-{category}.json"
        filepath = os.path.join(self.knowledge_dir, filename)
        
        # Add metadata
        learning["created_at"] = datetime.now().isoformat()
        learning["id"] = timestamp
        
        try:
            with open(filepath, "w") as f:
                json.dump(learning, f, indent=2)
            console.print(f"[green]✓ Learning saved to {filepath}[/green]")
            
            # Update AI.md
            self._update_ai_md()
            
            return filepath
        except Exception as e:
            console.print(f"[red]Failed to save learning: {e}[/red]")
            raise

    def search_knowledge(self, query: str = "", tags: List[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant learnings.
        
        Args:
            query: Text to search for in title/description (simple substring match for now).
            tags: List of tags to filter by.
            limit: Maximum number of results to return.
            
        Returns:
            List of learning dictionaries.
        """
        results = []
        files = glob.glob(os.path.join(self.knowledge_dir, "*.json"))
        
        # Sort by newest first
        files.sort(reverse=True)
        
        for filepath in files:
            try:
                with open(filepath, "r") as f:
                    learning = json.load(f)
                
                # Filter by tags
                if tags:
                    learning_tags = learning.get("tags", [])
                    # Also check category as a tag
                    learning_tags.append(learning.get("category", ""))
                    
                    if not any(tag.lower() in [t.lower() for t in learning_tags] for tag in tags):
                        continue
                
                # Filter by query
                if query:
                    search_text = f"{learning.get('title', '')} {learning.get('description', '')} {learning.get('content', '')}".lower()
                    if query.lower() not in search_text:
                        continue
                        
                results.append(learning)
                if len(results) >= limit:
                    break
                    
            except Exception:
                continue
                
        return results

    def get_all_learnings(self) -> List[Dict[str, Any]]:
        """Retrieve all learnings."""
        return self.search_knowledge(limit=1000)

    def get_context_string(self, query: str = "", tags: List[str] = None) -> str:
        """
        Get a formatted string of relevant learnings for context injection.
        """
        learnings = self.search_knowledge(query, tags)
        if not learnings:
            return "No relevant past learnings found."
            
        context = "## Relevant Past Learnings\n\n"
        for learning in learnings:
            context += f"### {learning.get('title', 'Untitled')}\n"
            context += f"- **Category**: {learning.get('category', 'General')}\n"
            context += f"- **Source**: {learning.get('source', 'Unknown')}\n"
            context += f"- **Date**: {learning.get('created_at', 'Unknown')}\n"
            content = learning.get('content', '')
            if isinstance(content, dict):
                context += f"\n{content.get('summary', '')}\n\n"
            else:
                context += f"\n{content}\n\n"
            if learning.get('codified_improvements'):
                context += "- **Improvements**:\n"
                for imp in learning['codified_improvements']:
                    context += f"  - [{imp.get('type', 'item')}] {imp.get('title', '')}: {imp.get('description', '')}\n"
            context += "\n"
            
        return context

    def _update_ai_md(self):
        """
        Update the AI.md file with a consolidated summary of all learnings.
        This file serves as a human-readable and LLM-friendly index.
        """
        learnings = self.get_all_learnings()
        
        # Group by category
        by_category = {}
        for learning in learnings:
            cat = learning.get("category", "General").title()
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(learning)
            
        content = "# AI Knowledge Base\n\n"
        content += "This file contains codified learnings and improvements for the AI system.\n"
        content += "It is automatically updated when new learnings are added.\n\n"
        
        for category, items in sorted(by_category.items()):
            content += f"## {category}\n\n"
            for item in items:
                content += f"### {item.get('title', 'Untitled')}\n"
                content += f"{item.get('description', '')}\n\n"
                
                if item.get('codified_improvements'):
                    content += "**Improvements:**\n"
                    for imp in item['codified_improvements']:
                        type_badge = f"[{imp.get('type', 'item').upper()}]"
                        content += f"- {type_badge} {imp.get('title', '')}: {imp.get('description', '')}\n"
                content += "\n"
                
        ai_md_path = os.path.join(self.knowledge_dir, "AI.md")
        try:
            with open(ai_md_path, "w") as f:
                f.write(content)
            console.print(f"[dim]Updated {ai_md_path}[/dim]")
        except Exception as e:
            console.print(f"[yellow]Failed to update AI.md: {e}[/yellow]")
