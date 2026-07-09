from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
from services.repo_service import clone_repo, build_tree, collect_scope_files, RepoError
from services.chunker import build_context_blob
from services.quiz_generator import generate_quiz, QuizGenerationError
from services.grader import grade_mcqs, grade_coding_task

app = FastAPI(title="Repo Quiz API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


class ImportRequest(BaseModel):
    repo_url: str


class GenerateRequest(BaseModel):
    repo_url: str
    scope_path: str


class SubmitRequest(BaseModel):
    repo_url: str
    scope_path: str
    quiz: dict
    mcq_answers: dict[str, int]
    coding_answer: str


@app.post("/api/repo/import")
def import_repo(req: ImportRequest):
    try:
        repo_path = clone_repo(req.repo_url)
        tree = build_tree(repo_path)
    except RepoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"tree": tree}


@app.post("/api/quiz/generate")
def generate(req: GenerateRequest):
    try:
        repo_path = clone_repo(req.repo_url)
        files = collect_scope_files(repo_path, req.scope_path)
        context_blob = build_context_blob(files)
        quiz = generate_quiz(req.scope_path, context_blob)
    except RepoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except QuizGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    quiz["files_used"] = [f["path"] for f in files]
    return quiz


@app.post("/api/quiz/submit")
def submit(req: SubmitRequest):
    mcq_results = grade_mcqs(req.quiz["mcqs"], req.mcq_answers)
    coding_result = grade_coding_task(req.quiz["coding_task"], req.coding_answer)

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
