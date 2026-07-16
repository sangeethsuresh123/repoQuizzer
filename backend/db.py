import json
from contextlib import contextmanager

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from config import DATABASE_URL
from models import Base, Repo, Attempt

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    pass  # schema managed by Alembic — run `alembic upgrade head` before starting


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_repo(repo_id: str, repo_url: str) -> None:
    with get_session() as session:
        existing = session.get(Repo, repo_id)
        if existing is None:
            session.add(Repo(id=repo_id, url=repo_url))
        # If it already exists, nothing to do — just ensure the row is there.


def save_attempt(repo_url, scope_path, created_at, quiz, answers, score, max_score):
    with get_session() as session:
        attempt = Attempt(
            repo_url=repo_url,
            scope_path=scope_path,
            created_at=created_at,
            quiz_json=json.dumps(quiz),
            answers_json=json.dumps(answers),
            score=score,
            max_score=max_score,
        )
        session.add(attempt)
        session.flush()  # populate attempt.id
        return attempt.id


def list_attempts():
    with get_session() as session:
        rows = (
            session.execute(
                select(Attempt).order_by(Attempt.id.desc())
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": r.id,
                "repo_url": r.repo_url,
                "scope_path": r.scope_path,
                "created_at": r.created_at,
                "score": r.score,
                "max_score": r.max_score,
            }
            for r in rows
        ]


def get_attempt(attempt_id: int):
    with get_session() as session:
        attempt = session.get(Attempt, attempt_id)
        if not attempt:
            return None
        return {
            "id": attempt.id,
            "repo_url": attempt.repo_url,
            "scope_path": attempt.scope_path,
            "created_at": attempt.created_at,
            "score": attempt.score,
            "max_score": attempt.max_score,
            "quiz": json.loads(attempt.quiz_json),
            "answers": json.loads(attempt.answers_json),
        }
