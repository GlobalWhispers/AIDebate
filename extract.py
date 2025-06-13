#!/usr/bin/env python3
"""
Extract script to read all project files and create a JSON structure.
Reads all .py, .md, .yml, .yaml files and organizes them in a nested directory structure.
Respects .gitignore patterns and skips virtual environments.

 python extract.py --preview

"""

import os
import json
import datetime
import fnmatch
from pathlib import Path
from typing import Dict, Any, Set, List


def parse_gitignore(gitignore_path: Path) -> List[str]:
    """Parse .gitignore file and return list of patterns."""
    patterns = []
    try:
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        patterns.append(line)
    except Exception as e:
        print(f"Warning: Could not read .gitignore: {e}")
    return patterns


def is_ignored_by_gitignore(file_path: Path, root_path: Path, gitignore_patterns: List[str]) -> bool:
    """Check if file is ignored by .gitignore patterns."""
    try:
        # Get relative path from root
        relative_path = file_path.relative_to(root_path)
        path_str = str(relative_path)
        path_parts = relative_path.parts

        for pattern in gitignore_patterns:
            # Handle different gitignore pattern types
            if pattern.endswith('/'):
                # Directory pattern
                pattern = pattern.rstrip('/')
                if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
                    return True
            elif '/' in pattern:
                # Path pattern
                if fnmatch.fnmatch(path_str, pattern):
                    return True
            else:
                # Filename pattern
                if fnmatch.fnmatch(file_path.name, pattern):
                    return True
                # Also check if any parent directory matches
                if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
                    return True
    except ValueError:
        # Path is not relative to root
        pass
    except Exception:
        # Any other error, don't ignore
        pass

    return False


def should_include_file(file_path: Path) -> bool:
    """Check if file should be included based on extension."""
    allowed_extensions = {'.py', '.md', '.yml', '.yaml', '.txt', '.json', '.toml', '.cfg', '.ini'}
    return file_path.suffix.lower() in allowed_extensions


def should_skip_directory(dir_name: str) -> bool:
    """Check if directory should be skipped (common build/cache directories)."""
    skip_dirs = {
        '__pycache__',
        '.git',
        '.pytest_cache',
        'node_modules',
        '.venv',
        'venv',
        'env',
        '.env',
        'ENV',
        'env.bak',
        'venv.bak',
        'dist',
        'build',
        '.idea',
        '.vscode',
        'htmlcov',
        '.coverage',
        '.mypy_cache',
        '.tox',
        '.cache',
        'eggs',
        '*.egg-info',
        '.eggs',
        'lib',
        'lib64',
        'parts',
        'sdist',
        'var',
        'wheels',
        'share/python-wheels',
        '*.egg-info/',
        '.installed.cfg',
        '*.egg',
        'MANIFEST',
        '.DS_Store',
        'Thumbs.db'
    }
    return dir_name in skip_dirs


def is_virtual_environment(dir_path: Path) -> bool:
    """Check if directory is a virtual environment."""
    venv_indicators = [
        'pyvenv.cfg',
        'Scripts/activate',
        'bin/activate',
        'Scripts/python.exe',
        'bin/python'
    ]

    for indicator in venv_indicators:
        if (dir_path / indicator).exists():
            return True

    # Check for common venv directory names
    venv_names = {'venv', '.venv', 'env', '.env', 'ENV', 'virtualenv'}
    if dir_path.name in venv_names:
        return True

    return False


def read_file_content(file_path: Path) -> str:
    """Read file content safely."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            return f"[Error reading file: {e}]"
    except Exception as e:
        return f"[Error reading file: {e}]"


def extract_directory_structure(root_path: Path, base_path: Path = None, gitignore_patterns: List[str] = None) -> Dict[
    str, Any]:
    """
    Recursively extract directory structure and file contents.

    Args:
        root_path: Path to extract from
        base_path: Base path for relative calculations (optional)
        gitignore_patterns: List of gitignore patterns to respect

    Returns:
        Dictionary with nested structure representing directories and files
    """
    if base_path is None:
        base_path = root_path

    if gitignore_patterns is None:
        gitignore_patterns = []

    structure = {}

    try:
        # Ensure we have a Path object
        if not isinstance(root_path, Path):
            root_path = Path(root_path)

        if not isinstance(base_path, Path):
            base_path = Path(base_path)

        # Check if path exists and is directory
        if not root_path.exists():
            return {"_error": f"Path does not exist: {root_path}"}

        if not root_path.is_dir():
            return {"_error": f"Path is not a directory: {root_path}"}

        # Get all items in directory
        items = list(root_path.iterdir())
        items.sort(key=lambda x: (x.is_file(), x.name.lower()))

        for item in items:
            try:
                # Check if item is ignored by gitignore
                if is_ignored_by_gitignore(item, base_path, gitignore_patterns):
                    continue

                # Skip hidden files except specific ones
                if item.name.startswith('.') and item.name not in {'.env.example', '.gitignore', '.gitattributes'}:
                    continue

                if item.is_dir():
                    # Skip certain directories
                    if should_skip_directory(item.name):
                        continue

                    # Skip virtual environments
                    if is_virtual_environment(item):
                        continue

                    # Recursively process subdirectories
                    substructure = extract_directory_structure(item, base_path, gitignore_patterns)
                    if substructure:  # Only add if not empty
                        structure[item.name] = {
                            "type": "directory",
                            "contents": substructure
                        }

                elif item.is_file():
                    # Only include certain file types
                    if should_include_file(item):
                        file_content = read_file_content(item)
                        try:
                            relative_path = str(item.relative_to(base_path))
                        except ValueError:
                            relative_path = str(item)

                        structure[item.name] = {
                            "type": "file",
                            "path": relative_path,
                            "extension": item.suffix,
                            "size": len(file_content),
                            "content": file_content
                        }

            except PermissionError:
                structure[f"_error_{item.name}"] = f"Permission denied accessing: {item.name}"
                continue
            except Exception as e:
                structure[f"_error_{item.name}"] = f"Error processing {item.name}: {e}"
                continue

    except PermissionError as e:
        structure["_error"] = f"Permission denied: {e}"
    except Exception as e:
        structure["_error"] = f"Error processing directory: {e}"

    return structure


def count_items_recursive(structure: Dict[str, Any]) -> Dict[str, int]:
    """Count files and directories recursively."""
    counts = {
        "files": 0,
        "directories": 0,
        "total_size": 0,
        "file_types": {}
    }

    for name, item in structure.items():
        if name.startswith("_"):
            continue

        if isinstance(item, dict):
            if item.get("type") == "directory":
                counts["directories"] += 1
                sub_counts = count_items_recursive(item.get("contents", {}))
                counts["files"] += sub_counts["files"]
                counts["directories"] += sub_counts["directories"]
                counts["total_size"] += sub_counts["total_size"]

                # Merge file types
                for ext, count in sub_counts["file_types"].items():
                    counts["file_types"][ext] = counts["file_types"].get(ext, 0) + count

            elif item.get("type") == "file":
                counts["files"] += 1
                ext = item.get("extension", "")
                counts["file_types"][ext] = counts["file_types"].get(ext, 0) + 1
                counts["total_size"] += item.get("size", 0)

    return counts


def create_project_metadata(root_path: Path, structure: Dict[str, Any]) -> Dict[str, Any]:
    """Create metadata about the project."""
    counts = count_items_recursive(structure)

    metadata = {
        "project_name": root_path.name,
        "extraction_timestamp": datetime.datetime.now().isoformat(),
        "root_path": str(root_path.absolute()),
        "total_files": counts["files"],
        "total_directories": counts["directories"],
        "file_types": counts["file_types"],
        "total_size": counts["total_size"],
        "respects_gitignore": True,
        "skips_virtual_environments": True
    }

    return metadata


def preview_structure(structure: Dict[str, Any], indent: int = 0) -> None:
    """Preview the extracted structure."""
    prefix = "  " * indent

    for name, item in structure.items():
        if name.startswith("_"):
            continue

        if isinstance(item, dict):
            if item.get("type") == "directory":
                print(f"{prefix}📁 {name}/")
                preview_structure(item.get("contents", {}), indent + 1)
            elif item.get("type") == "file":
                size = item.get("size", 0)
                ext = item.get("extension", "")
                print(f"{prefix}📄 {name} ({size:,} chars, {ext})")


def main():
    """Main extraction function."""
    # Get current directory or specified directory
    import sys

    if len(sys.argv) > 1:
        root_dir = Path(sys.argv[1])
    else:
        root_dir = Path.cwd()

    # Ensure we have a Path object
    if not isinstance(root_dir, Path):
        root_dir = Path(root_dir)

    if not root_dir.exists():
        print(f"Error: Directory {root_dir} does not exist")
        return

    if not root_dir.is_dir():
        print(f"Error: {root_dir} is not a directory")
        return

    print(f"🔍 Extracting project structure from: {root_dir.absolute()}")
    print("📁 Reading all .py, .md, .yml, .yaml, .txt, .json files...")

    # Parse .gitignore if it exists
    gitignore_path = root_dir / '.gitignore'
    gitignore_patterns = parse_gitignore(gitignore_path)

    if gitignore_patterns:
        print(f"📋 Found .gitignore with {len(gitignore_patterns)} patterns")
    else:
        print("📋 No .gitignore found or empty")

    print("🚫 Skipping virtual environments and build directories")

    # Extract the directory structure
    try:
        structure = extract_directory_structure(root_dir, gitignore_patterns=gitignore_patterns)

        # Create metadata
        metadata = create_project_metadata(root_dir, structure)

        # Create project data
        project_data = {
            "metadata": metadata,
            "structure": structure
        }

        # Output filename
        output_file = root_dir / "project.json"

        # Write JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Extraction complete!")
        print(f"📊 Statistics:")
        print(f"   • Total files: {metadata['total_files']}")
        print(f"   • Total directories: {metadata['total_directories']}")
        print(f"   • Total size: {metadata['total_size']:,} characters")
        print(f"📄 Output saved to: {output_file}")

        # Show file type breakdown
        if metadata['file_types']:
            print(f"\n📋 File type breakdown:")
            for ext, count in sorted(metadata['file_types'].items()):
                ext_name = ext if ext else "(no extension)"
                print(f"   • {ext_name}: {count} files")

    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Add preview option
    import sys

    if "--preview" in sys.argv:
        sys.argv.remove("--preview")

        # Get directory
        if len(sys.argv) > 1:
            root_dir = Path(sys.argv[1])
        else:
            root_dir = Path.cwd()

        # Parse .gitignore
        gitignore_path = root_dir / '.gitignore'
        gitignore_patterns = parse_gitignore(gitignore_path)

        print(f"🔍 Preview of project structure: {root_dir.name}")
        if gitignore_patterns:
            print(f"📋 Respecting .gitignore with {len(gitignore_patterns)} patterns")
        print("=" * 50)

        structure = extract_directory_structure(root_dir, gitignore_patterns=gitignore_patterns)
        preview_structure(structure)

    else:
        main()
