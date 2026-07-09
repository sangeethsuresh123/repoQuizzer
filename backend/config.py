import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
REPOS_DIR = STORAGE_DIR / "repos"
DB_PATH = STORAGE_DIR / "quiz_history.db"

REPOS_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
LLAMA_MODEL = os.environ.get("LLAMA_MODEL", "meta/llama-3.2-1b-instruct")

# Limits to keep clones and prompts small/fast for a portfolio demo
MAX_FILE_BYTES = 60_000          # skip individual files bigger than this
MAX_TOTAL_CHUNK_CHARS = 10_000   # cap on combined text sent to the LLM per quiz (kept small: 1B model)
CLONE_TIMEOUT_SECONDS = 45

# Extensions we consider "code" for language detection / filtering
CODE_EXTENSIONS = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".rb": "Ruby", ".php": "PHP", ".c": "C", ".h": "C",
    ".cpp": "C++", ".hpp": "C++", ".cs": "C#", ".swift": "Swift",
    ".kt": "Kotlin", ".scala": "Scala", ".sh": "Shell", ".sql": "SQL",
}

IGNORED_DIR_NAMES = {
    ".git", "node_modules", "dist", "build", "__pycache__", ".venv",
    "venv", ".next", "vendor", "target", ".idea", ".vscode", "coverage",
}
