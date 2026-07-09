import sqlite3
import json
from contextlib import contextmanager
from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_url TEXT NOT NULL,
                scope_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                quiz_json TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                score INTEGER NOT NULL,
                max_score INTEGER NOT NULL
            )
            """
        )


def save_attempt(repo_url, scope_path, created_at, quiz, answers, score, max_score):
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO attempts (repo_url, scope_path, created_at, quiz_json, answers_json, score, max_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo_url,
                scope_path,
                created_at,
                json.dumps(quiz),
                json.dumps(answers),
                score,
                max_score,
            ),
        )
        return cur.lastrowid


def list_attempts():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, repo_url, scope_path, created_at, score, max_score FROM attempts ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_attempt(attempt_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["quiz"] = json.loads(data.pop("quiz_json"))
        data["answers"] = json.loads(data.pop("answers_json"))
        return data
