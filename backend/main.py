import asyncio
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import db
from services.repo_service import clone_repo, build_tree, collect_scope_files, slug_for_url, RepoError
from services.embedder import embed_repo
from services.ask import ask
from services.chunker import build_context_blob
from services.quiz_generator import (
    generate_quiz, generate_fallback_quiz, QuizGenerationError, QUIZ_TIMEOUT_SECONDS,
)
from services.grader import grade_mcqs, grade_coding_task

try:
    from openai import APITimeoutError
except ImportError:
    APITimeoutError = None  # type: ignore[assignment,misc]

logger = logging.getLogger("repoquiz")

GENERATE_TOTAL_TIMEOUT = 200  # hard cap on entire generate endpoint

app = FastAPI(title="Repo Quiz API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


class ImportRequest(BaseModel):
    repo_url: str


class GenerateRequest(BaseModel):
    repo_url: str
    scope_path: str
    previous_questions: list[str] = []


class SubmitRequest(BaseModel):
    repo_url: str
    scope_path: str
    quiz: dict
    mcq_answers: dict[str, int]
    coding_answer: str


class AskRequest(BaseModel):
    repo_id: str
    question: str


@app.post("/api/repo/import")
async def import_repo(req: ImportRequest):
    try:
        repo_path = await asyncio.to_thread(clone_repo, req.repo_url)
        tree = await asyncio.to_thread(build_tree, repo_path)
        repo_id = slug_for_url(req.repo_url)
        db.upsert_repo(repo_id, req.repo_url)
        try:
            await asyncio.to_thread(embed_repo, repo_id, req.repo_url, repo_path)
        except Exception as e:
            logger.warning("Embedding failed (chat will be unavailable): %s", e)
    except RepoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"tree": tree, "repo_id": repo_id}


async def _do_generate(req: GenerateRequest) -> dict:
    repo_path = await asyncio.to_thread(clone_repo, req.repo_url)
    files = await asyncio.to_thread(collect_scope_files, repo_path, req.scope_path)
    context_blob = await asyncio.to_thread(build_context_blob, files)

    try:
        logger.info("Calling LLM for quiz generation...")
        quiz = await asyncio.wait_for(
            asyncio.to_thread(
                generate_quiz, req.scope_path, context_blob, req.previous_questions
            ),
            timeout=QUIZ_TIMEOUT_SECONDS,
        )
        logger.info("LLM quiz generation succeeded")
    except asyncio.TimeoutError:
        logger.warning("LLM timed out, using fallback quiz")
        quiz = await asyncio.to_thread(generate_fallback_quiz, req.scope_path, files)
    except QuizGenerationError as e:
        logger.warning(f"QuizGenerationError, using fallback: {e}")
        quiz = await asyncio.to_thread(generate_fallback_quiz, req.scope_path, files)
    except Exception as e:
        logger.error(f"Unexpected error in generate: {type(e).__name__}: {e}")
        if APITimeoutError is not None and isinstance(e, APITimeoutError):
            logger.warning("OpenAI timeout, using fallback quiz")
            quiz = await asyncio.to_thread(generate_fallback_quiz, req.scope_path, files)
        else:
            raise

    quiz["files_used"] = [f["path"] for f in files]
    return quiz


@app.post("/api/quiz/generate")
async def generate(req: GenerateRequest):
    try:
        quiz = await asyncio.wait_for(_do_generate(req), timeout=GENERATE_TOTAL_TIMEOUT)
    except RepoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except QuizGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Quiz generation timed out. The LLM may be unavailable — try again later.",
        )
    return quiz


GRADING_TIMEOUT_SECONDS = 120

@app.post("/api/quiz/submit")
async def submit(req: SubmitRequest):
    def _grade():
        mcq_results = grade_mcqs(req.quiz["mcqs"], req.mcq_answers)
        coding_result = grade_coding_task(req.quiz["coding_task"], req.coding_answer)
        return mcq_results, coding_result

    try:
        mcq_results, coding_result = await asyncio.wait_for(
            asyncio.to_thread(_grade),
            timeout=GRADING_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        mcq_results = grade_mcqs(req.quiz["mcqs"], req.mcq_answers)
        coding_result = {"correct": None, "feedback": "Grading timed out."}

    mcq_score = sum(1 for r in mcq_results if r["is_correct"])
    coding_score = 1 if coding_result.get("correct") else 0
    max_score = len(mcq_results) + 1

    attempt_id = db.save_attempt(
        repo_url=req.repo_url,
        scope_path=req.scope_path,
        created_at=datetime.now(timezone.utc).isoformat(),
        quiz=req.quiz,
        answers={"mcq_answers": req.mcq_answers, "coding_answer": req.coding_answer},
        score=mcq_score + coding_score,
        max_score=max_score,
    )

    return {
        "attempt_id": attempt_id,
        "mcq_results": mcq_results,
        "coding_result": coding_result,
        "score": mcq_score + coding_score,
        "max_score": max_score,
    }


@app.get("/api/history")
def history():
    return {"attempts": db.list_attempts()}


@app.get("/api/history/{attempt_id}")
def history_detail(attempt_id: int):
    attempt = db.get_attempt(attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    return attempt


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/debug/chunks/{repo_id:path}")
def debug_chunks(repo_id: str):
    from services.embedder import _normalize_repo_id
    repo_id = _normalize_repo_id(repo_id)
    try:
        with db.get_session() as session:
            from models import RepoChunk
            count = session.query(RepoChunk).filter(RepoChunk.repo_id == repo_id).count()
            sample = session.query(RepoChunk).filter(RepoChunk.repo_id == repo_id).limit(2).all()
            return {
                "repo_id": repo_id,
                "chunk_count": count,
                "samples": [{"file_path": s.file_path, "text_len": len(s.text), "text_preview": s.text[:200]} for s in sample],
            }
    except Exception as e:
        return {"repo_id": repo_id, "error": str(e)}


@app.post("/api/ask")
async def ask_question(req: AskRequest):
    try:
        result = await asyncio.to_thread(ask, req.repo_id, req.question)
    except Exception as e:
        logger.error("ask failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return result
