#!/usr/bin/env python3
"""
Audit Python imports across the repo and report what cannot be imported.
- Recursively scans .py files (excluding venv, node_modules, frontend)
- Tries to import top-level modules; lists what's missing
- Maps common module->PyPI package names to help you install the right thing
Run:
  python tools/audit_deps.py
"""

import os, sys, ast, importlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IGNORE_DIRS = {".venv", "venv", "node_modules", "frontend", "frontend_old", "__pycache__", ".git"}
COMMON_MAP = {
    "dotenv": "python-dotenv",
    "fastapi": "fastapi",
    "starlette": "starlette",
    "uvicorn": "uvicorn",
    "sqlalchemy": "SQLAlchemy",
    "alembic": "alembic",
    "psycopg2": "psycopg2-binary",
    "passlib": "passlib[bcrypt]",
    "jose": "python-jose[cryptography]",
    "email_validator": "email-validator",
    "multipart": "python-multipart",
    "pydantic": "pydantic",
    "stripe": "stripe",
    "requests": "requests",
    "loguru": "loguru",
    "redis": "redis",
    "boto3": "boto3",
    "python_dotenv": "python-dotenv",
}

def iter_py_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        # prune ignored dirs
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                yield Path(dirpath) / f

def top_level_imports(pyfile: Path):
    try:
        tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    except Exception:
        return set()
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                mods.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    return mods

def is_stdlib(module: str) -> bool:
    # best-effort: try import and inspect module path
    try:
        m = importlib.import_module(module)
        p = getattr(m, "__file__", "") or ""
        return ("site-packages" not in p) and ("dist-packages" not in p)
    except Exception:
        return False

def main():
    modules = set()
    for py in iter_py_files(REPO_ROOT):
        modules |= top_level_imports(py)

    missing = {}
    for mod in sorted(modules):
        if mod in {"__future__", "typing"}:
            continue
        try:
            importlib.import_module(mod)
        except Exception:
            # skip stdlib-looking names
            if not is_stdlib(mod):
                missing[mod] = COMMON_MAP.get(mod, mod)

    if not missing:
        print("✅ All imports resolved in current environment.")
    else:
        print("❌ Missing imports detected:\n")
        for mod, pkg in missing.items():
            line = f"  - import '{mod}'  →  PyPI package: {pkg}"
            print(line)
        print("\nInstall suggestions:")
        print("pip install " + " ".join(sorted(set(missing.values()))))

if __name__ == "__main__":
    sys.path.insert(0, str(REPO_ROOT))
    main()
