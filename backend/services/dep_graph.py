"""
Build a dependency graph for a cloned repo.

Scans code files for import/require/use statements and resolves
them to relative file paths, producing a graph of
  {nodes: [{id, path, language}], edges: [{source, target}]}

Handles: Python, JS/TS/JSX/TSX, Go, Rust, Java.
"""

import re
from pathlib import Path

from config import CODE_EXTENSIONS, IGNORED_DIR_NAMES

# Patterns grouped by file extension
_IMPORT_PATTERNS: dict[str, list[re.Pattern]] = {
    ".py": [
        re.compile(r"^\s*from\s+([\w.]+)\s+import\b"),
        re.compile(r"^\s*import\s+([\w.]+)"),
    ],
    ".js": [
        re.compile(r"""(?:import|export)\s+.*?from\s+['"](.+?)['"]"""),
        re.compile(r"""require\s*\(\s*['"](.+?)['"]\s*\)"""),
    ],
    ".jsx": [
        re.compile(r"""(?:import|export)\s+.*?from\s+['"](.+?)['"]"""),
        re.compile(r"""require\s*\(\s*['"](.+?)['"]\s*\)"""),
    ],
    ".ts": [
        re.compile(r"""(?:import|export)\s+.*?from\s+['"](.+?)['"]"""),
        re.compile(r"""require\s*\(\s*['"](.+?)['"]\s*\)"""),
        re.compile(r"""import\s*\(\s*['"](.+?)['"]\s*\)"""),
    ],
    ".tsx": [
        re.compile(r"""(?:import|export)\s+.*?from\s+['"](.+?)['"]"""),
        re.compile(r"""require\s*\(\s*['"](.+?)['"]\s*\)"""),
        re.compile(r"""import\s*\(\s*['"](.+?)['"]\s*\)"""),
    ],
    ".go": [
        re.compile(r"""(?:import\s+(?:\(\s*)?["'](.+?)["'])"""),
    ],
    ".rs": [
        re.compile(r"""^\s*use\s+([\w:]+)"""),
        re.compile(r"""^\s*mod\s+(\w+)"""),
        re.compile(r"""^\s*extern\s+crate\s+(\w+)"""),
    ],
    ".java": [
        re.compile(r"""^\s*import\s+([\w.]+)"""),
    ],
}

# Packages that are stdlib / third-party — skip these
_STDLIB_PYTHON = {
    "os", "sys", "re", "json", "math", "datetime", "pathlib", "typing",
    "collections", "functools", "itertools", "logging", "hashlib",
    "subprocess", "shutil", "io", "time", "random", "unittest", "abc",
    "copy", "enum", "dataclasses", "contextlib", "argparse", "http",
    "urllib", "email", "html", "xml", "csv", "sqlite3", "struct",
    "socket", "threading", "multiprocessing", "asyncio", "pprint",
    "textwrap", "string", "calendar", "locale", "gettext", "getpass",
    "platform", "signal", "stat", "tempfile", "glob", "fnmatch",
}

_STDLIB_JS = {
    "fs", "path", "http", "https", "url", "crypto", "os", "child_process",
    "util", "events", "stream", "buffer", "net", "tls", "dns", "readline",
    "zlib", "cluster", "process", "assert", "querystring", "perf_hooks",
    "worker_threads", "v8", "vm", "string_decoder", "timers", "console",
    "assert/strict", "node:path", "node:fs", "node:http", "node:os",
}

_MAX_NODES = 60
_LANGUAGE_COLORS: dict[str, str] = {
    "Python": "#3572A5",
    "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6",
    "Go": "#00ADD8",
    "Rust": "#DEA584",
    "Java": "#B07219",
    "C": "#555555",
    "C++": "#F34B7D",
    "C#": "#178600",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Scala": "#C22D40",
    "SQL": "#e38c00",
    "Shell": "#89e051",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
}


def build_dep_graph(repo_path: Path) -> dict:
    """Return {nodes: [...], edges: [...]} for the repo."""
    code_files: list[tuple[str, Path]] = []
    all_files: set[str] = set()

    for fpath in repo_path.rglob("*"):
        if fpath.is_dir():
            continue
        rel = fpath.relative_to(repo_path)
        if any(part in IGNORED_DIR_NAMES or part.startswith(".") for part in rel.parts):
            continue
        ext = fpath.suffix.lower()
        if ext not in CODE_EXTENSIONS:
            continue
        file_id = str(rel)
        code_files.append((file_id, fpath))
        all_files.add(file_id)

    nodes: list[dict] = []
    edges_set: set[tuple[str, str]] = set()

    for file_id, fpath in code_files:
        ext = fpath.suffix.lower()
        lang = CODE_EXTENSIONS.get(ext, "Unknown")
        nodes.append({
            "id": file_id,
            "path": file_id,
            "language": lang,
            "color": _LANGUAGE_COLORS.get(lang, "#8B949E"),
        })

        patterns = _IMPORT_PATTERNS.get(ext, [])
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for line in content.splitlines():
            for pat in patterns:
                m = pat.search(line)
                if not m:
                    continue
                raw = m.group(1)
                targets = _resolve_import(raw, file_id, ext, repo_path, all_files)
                for target in targets:
                    if target != file_id:
                        edges_set.add((file_id, target))
                break

    if len(nodes) > _MAX_NODES:
        degree: dict[str, int] = {n["id"]: 0 for n in nodes}
        for s, t in edges_set:
            degree[s] = degree.get(s, 0) + 1
            degree[t] = degree.get(t, 0) + 1
        top = sorted(degree, key=degree.get, reverse=True)[:_MAX_NODES]
        top_set = set(top)
        nodes = [n for n in nodes if n["id"] in top_set]
        edges_set = {(s, t) for s, t in edges_set if s in top_set and t in top_set}

    edges = [{"source": s, "target": t} for s, t in edges_set]

    return {"nodes": nodes, "edges": edges}


def _resolve_import(
    raw: str, importer_id: str, ext: str, repo_path: Path, all_files: set[str]
) -> list[str]:
    """Best-effort resolve a raw import string to file IDs in the repo."""
    if ext == ".py":
        return _resolve_python(raw, importer_id, all_files)
    if ext in (".js", ".jsx", ".ts", ".tsx"):
        return _resolve_js_ts(raw, importer_id, all_files)
    if ext == ".go":
        return _resolve_go(raw, importer_id, all_files)
    if ext == ".rs":
        return _resolve_rust(raw, importer_id, all_files)
    if ext == ".java":
        return _resolve_java(raw, all_files)
    return []


def _resolve_python(raw: str, importer_id: str, all_files: set[str]) -> list[str]:
    parts = raw.split(".")
    if parts[0].lower() in _STDLIB_PYTHON or parts[0] in _STDLIB_PYTHON:
        return []

    # Relative import
    if importer_id.count("/") > 0:
        pkg_dir = str(Path(importer_id).parent)
    else:
        pkg_dir = ""

    candidates = []
    # Try as module file
    for path_variant in [
        "/".join(parts) + ".py",
        "/".join(parts) + "/__init__.py",
    ]:
        if path_variant in all_files:
            candidates.append(path_variant)

    # Try relative
    if pkg_dir:
        for path_variant in [
            pkg_dir + "/" + "/".join(parts) + ".py",
            pkg_dir + "/" + "/".join(parts) + "/__init__.py",
        ]:
            if path_variant in all_files:
                candidates.append(path_variant)

    # Try dropping last part (from X.Y import Z → try X.Y)
    if len(parts) > 1:
        parent = "/".join(parts[:-1])
        for path_variant in [
            parent + ".py",
            parent + "/__init__.py",
        ]:
            if path_variant in all_files:
                candidates.append(path_variant)

    return list(set(candidates))


def _resolve_js_ts(raw: str, importer_id: str, all_files: set[str]) -> list[str]:
    if not raw.startswith("."):
        # Package import
        pkg = raw.split("/")[0].lower()
        if pkg in _STDLIB_JS or pkg.startswith("node:"):
            return []
        return []

    # Relative import
    base = Path(importer_id).parent
    candidates = []
    for ext_suffix in ("", ".ts", ".tsx", ".js", ".jsx"):
        candidate = str((base / (raw + ext_suffix)).as_posix())
        if candidate in all_files:
            candidates.append(candidate)
    # Try as directory/index
    for ext_suffix in (".ts", ".tsx", ".js", ".jsx"):
        candidate = str((base / raw / ("index" + ext_suffix)).as_posix())
        if candidate in all_files:
            candidates.append(candidate)
    return candidates


def _resolve_go(raw: str, importer_id: str, all_files: set[str]) -> list[str]:
    if raw.startswith("."):
        base = Path(importer_id).parent
        candidate = str((base / raw.lstrip(".")).with_suffix(".go").as_posix())
        if candidate in all_files:
            return [candidate]
    return []


def _resolve_rust(raw: str, importer_id: str, all_files: set[str]) -> list[str]:
    parts = raw.split("::")
    base = Path(importer_id).parent
    candidates = []
    for suffix in (".rs",):
        candidate = str((base / "/".join(parts)).with_suffix(suffix).as_posix())
        if candidate in all_files:
            candidates.append(candidate)
    candidate = str((base / "/".join(parts) / "mod.rs").as_posix())
    if candidate in all_files:
        candidates.append(candidate)
    return candidates


def _resolve_java(raw: str, all_files: set[str]) -> list[str]:
    parts = raw.split(".")
    if len(parts) >= 2:
        # Try as file
        candidate = "/".join(parts) + ".java"
        if candidate in all_files:
            return [candidate]
    return []
