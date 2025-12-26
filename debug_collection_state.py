import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from rich.console import Console

from utils.knowledge.core import KnowledgeBase

console = Console()


def debug_collection():
    # Initialize KB to get the correct dynamic collection name
    kb = KnowledgeBase()
    collection_name = kb.codebase_indexer.collection_name

    console.print(f"[bold cyan]Inspecting Collection: {collection_name}[/bold cyan]")

    client = kb.client
    if not client:
        console.print("[red]No Qdrant client connection.[/red]")
        return

    if not client.collection_exists(collection_name):
        console.print(f"[red]Collection '{collection_name}' does not exist.[/red]")
        return

    info = client.get_collection(collection_name)
    vectors_config = info.config.params.vectors

    console.print(f"Vectors Config Type: {type(vectors_config)}")
    console.print(f"Vectors Config Raw: {vectors_config}")

    # Simulate the check logic from indexer.py
    existing_size = None
    if isinstance(vectors_config, dict):
        console.print("Config is DICT")
        if "" in vectors_config:
            existing_size = vectors_config[""].size
        elif len(vectors_config) == 1:
            existing_size = list(vectors_config.values())[0].size
        else:
            console.print(f"Complex dict keys: {vectors_config.keys()}")

    elif hasattr(vectors_config, "size"):
        console.print("Config has .size attribute")
        existing_size = vectors_config.size
    else:
        console.print("Config matches NEITHER dict nor object with .size")

    console.print(f"Detected Existing Size: {existing_size}")


if __name__ == "__main__":
    debug_collection()
