import hashlib
import subprocess
from pathlib import Path

from config import (
    REPOS_DIR, CLONE_TIMEOUT_SECONDS, MAX_FILE_BYTES,
    CODE_EXTENSIONS, IGNORED_DIR_NAMES,
)


class RepoError(Exception):
    pass


def _slug_for_url(repo_url: str) -> str:
    h = hashlib.sha1(repo_url.encode()).hexdigest()[:12]
    name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    return f"{name}-{h}"


def clone_repo(repo_url: str) -> Path:
    """Clone (or reuse an existing shallow clone of) a public GitHub repo. Returns local path."""
    if "github.com" not in repo_url:
        raise RepoError("Only public GitHub repository URLs are supported right now.")

    dest = REPOS_DIR / _slug_for_url(repo_url)
    if dest.exists() and any(dest.iterdir()):
        return dest  # already cloned, reuse it

    dest.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(dest)],
            check=True,
            timeout=CLONE_TIMEOUT_SECONDS,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise RepoError(f"git clone failed: {e.stderr.strip()[:300]}")
    except subprocess.TimeoutExpired:
        raise RepoError("Cloning timed out. The repo may be too large for this demo.")

    return dest


def _is_code_file(path: Path) -> bool:
    return path.suffix.lower() in CODE_EXTENSIONS


def build_tree(repo_path: Path) -> dict:
    """Return a nested tree of code files/folders under repo_path (dirs like .git filtered out)."""

    def walk(dir_path: Path) -> dict:
        node = {"name": dir_path.name or repo_path.name, "type": "dir", "children": []}
        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return node
        for entry in entries:
            if entry.name in IGNORED_DIR_NAMES or entry.name.startswith("."):
                continue
            if entry.is_dir():
                child = walk(entry)
                if child["children"]:
                    node["children"].append(child)
            elif _is_code_file(entry):
                rel = str(entry.relative_to(repo_path))
                node["children"].append({
                    "name": entry.name,
                    "type": "file",
                    "path": rel,
                    "language": CODE_EXTENSIONS.get(entry.suffix.lower(), "Unknown"),
                })
        return node

    return walk(repo_path)


def collect_scope_files(repo_path: Path, scope_rel_path: str) -> list[dict]:
    """Given a relative path (file or folder) inside the repo, return a list of
    {path, language, content} dicts for every code file in that scope."""
    target = (repo_path / scope_rel_path).resolve()
    if not str(target).startswith(str(repo_path.resolve())):
        raise RepoError("Invalid scope path.")
    if not target.exists():
        raise RepoError("Scope path not found in repo.")

    files = []
    candidates = [target] if target.is_file() else sorted(target.rglob("*"))
    for path in candidates:
        if path.is_dir():
            continue
        if any(part in IGNORED_DIR_NAMES for part in path.parts):
            continue
        if not _is_code_file(path):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        files.append({
            "path": str(path.relative_to(repo_path)),
            "language": CODE_EXTENSIONS.get(path.suffix.lower(), "Unknown"),
            "content": content,
        })
    if not files:
        raise RepoError("No readable code files found in that scope.")
    return files
