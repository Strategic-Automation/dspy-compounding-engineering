#!/usr/bin/env python3
"""
Auto-generate API documentation from Python docstrings and type hints.

Scans agents/, workflows/, utils/, config.py, and cli.py to build
a structured API reference. Output goes to docs/api/.

Usage:
    python scripts/generate_api_docs.py [--output-dir docs/api]
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path


def extract_docstring(source: str) -> str:
    """Extract the module-level docstring from source code."""
    try:
        tree = ast.parse(source)
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
        ):
            return tree.body[0].value.value.strip()
    except SyntaxError:
        pass
    return "No module documentation available."


def extract_classes_and_functions(source: str) -> list:
    """Extract public class and function definitions with docstrings."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    items = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            doc = ast.get_docstring(node) or "No documentation available."
            methods = []
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and not child.name.startswith("_"):
                    mdoc = ast.get_docstring(child) or ""
                    args = [a.arg for a in child.args.args if a.arg != "self"]
                    methods.append({"name": child.name, "args": args, "doc": mdoc})
            items.append({"kind": "class", "name": node.name, "doc": doc, "methods": methods})

        elif isinstance(node, ast.FunctionDef):
            if node.name.startswith("_"):
                continue
            doc = ast.get_docstring(node) or "No documentation available."
            args = [a.arg for a in node.args.args]
            items.append({"kind": "function", "name": node.name, "doc": doc, "args": args})

    return items


def generate_module_docs(module_path: str, base_dir: str) -> str:
    """Generate markdown API docs for a single module file."""
    rel = os.path.relpath(module_path, base_dir)
    module_name = rel.replace(os.sep, ".").replace(".py", "")
    if module_name.endswith(".__init__"):
        module_name = module_name.rsplit(".", 1)[0]

    try:
        with open(module_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return ""

    module_doc = extract_docstring(source)
    items = extract_classes_and_functions(source)

    md = f"## `{module_name}`\n\n"
    md += f"{module_doc}\n\n"

    if items:
        for item in items:
            if item["kind"] == "class":
                md += f"### {item['name']}\n\n"
                md += f"{item['doc']}\n\n"
                if item["methods"]:
                    md += "#### Methods\n\n"
                    for method in item["methods"]:
                        md += f"- `{method['name']}({', '.join(method['args'])})`"
                        if method["doc"]:
                            first_line = method["doc"].split("\n")[0]
                            md += f" -- {first_line}"
                        md += "\n"
                    md += "\n"
            elif item["kind"] == "function":
                md += f"### `{item['name']}({', '.join(item['args'])})`\n\n"
                md += f"{item['doc']}\n\n"

    return md


def walk_directory(directory: str, base_dir: str) -> str:
    """Walk a directory and generate markdown for all Python files."""
    md = ""
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".venv", "node_modules")]

        py_files = sorted([f for f in files if f.endswith(".py") and f != "__init__.py"])
        if "cli.py" not in [f for f in py_files]:
            pass

        # Handle __init__.py
        init_path = os.path.join(root, "__init__.py")
        if os.path.exists(init_path):
            init_doc = generate_module_docs(init_path, base_dir)
            if init_doc:
                md += init_doc + "\n---\n\n"

        for py_file in py_files:
            fpath = os.path.join(root, py_file)
            module_md = generate_module_docs(fpath, base_dir)
            if module_md:
                md += module_md + "\n---\n\n"

    return md


def main():
    parser = argparse.ArgumentParser(description="Auto-generate API docs from Python source")
    parser.add_argument(
        "--output-dir",
        default="docs/api",
        help="Output directory for generated API docs",
    )
    args = parser.parse_args()

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated = []

    # Generate agents API
    agents_md = "# Agents API Reference\n\n"
    agents_md += "Auto-generated from docstrings. Do not edit manually.\n\n"
    agents_md += "---\n\n"
    if os.path.isdir("agents"):
        agents_md += walk_directory("agents", ".")
    with open(output_path / "agents.md", "w") as f:
        f.write(agents_md)
    generated.append("agents.md")
    print(f"  Generated docs/api/agents.md")

    # Generate workflows API
    workflows_md = "# Workflows API Reference\n\n"
    workflows_md += "Auto-generated from docstrings. Do not edit manually.\n\n"
    workflows_md += "---\n\n"
    if os.path.isdir("workflows"):
        workflows_md += walk_directory("workflows", ".")
    with open(output_path / "workflows.md", "w") as f:
        f.write(workflows_md)
    generated.append("workflows.md")
    print(f"  Generated docs/api/workflows.md")

    # Generate utilities API
    utilities_md = "# Utilities API Reference\n\n"
    utilities_md += "Auto-generated from docstrings. Do not edit manually.\n\n"
    utilities_md += "---\n\n"
    if os.path.isdir("utils"):
        utilities_md += walk_directory("utils", ".")
    with open(output_path / "utilities.md", "w") as f:
        f.write(utilities_md)
    generated.append("utilities.md")
    print(f"  Generated docs/api/utilities.md")

    # Generate config + CLI API
    config_md = "# Configuration & CLI API Reference\n\n"
    config_md += "Auto-generated from docstrings. Do not edit manually.\n\n"
    config_md += "---\n\n"
    for mod_file in ["config.py", "cli.py"]:
        if os.path.isfile(mod_file):
            config_md += generate_module_docs(mod_file, ".") + "\n---\n\n"
    with open(output_path / "config.md", "w") as f:
        f.write(config_md)
    generated.append("config.md")
    print(f"  Generated docs/api/config.md")

    print(f"Done. Generated {len(generated)} API documentation files.")


if __name__ == "__main__":
    main()
