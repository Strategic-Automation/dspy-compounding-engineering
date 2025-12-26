from utils.io import get_project_context

context = get_project_context(task="Refactor config.py to remove global state")
print(f"Context length: {len(context)}")
print("First 200 chars:")
print(context[:200])
