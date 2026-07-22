"""
Pure Python TF-IDF embedder for the "Chat with the repo" RAG feature.

Zero heavy dependencies — uses only stdlib (collections, math, json).
Stores chunks in Postgres, computes cosine similarity at query time.
Fits easily in Render's 512 MB free-tier RAM.
"""

import logging
import math
from collections import Counter
from pathlib import Path

from services.repo_service import collect_scope_files, slug_for_url

logger = logging.getLogger("repoquiz.embedder")

CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 200


def _normalize_repo_id(repo_id: str) -> str:
    if repo_id.startswith("http"):
        return slug_for_url(repo_id)
    return repo_id


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _build_vocab(texts: list[str], max_features: int = 2048) -> dict[str, int]:
    counter: Counter = Counter()
    for t in texts:
        counter.update(_tokenize(t))
    return {word: i for i, (word, _) in enumerate(counter.most_common(max_features))}


def _vectorize(text: str, vocab: dict[str, int]) -> dict[int, float]:
    tokens = _tokenize(text)
    if not tokens or not vocab:
        return {}
    tf = Counter(tokens)
    total = len(tokens)
    return {vocab[tok]: count / total for tok, count in tf.items() if tok in vocab}


def _cosine(a: dict[int, float], b: dict[int, float]) -> float:
    dot = sum(a[k] * b[k] for k in a if k in b)
    if dot == 0:
        return 0.0
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_chunks(repo_id: str, query_text: str, top_k: int = 5) -> list[dict]:
    from db import get_session
    from models import RepoChunk

    repo_id = _normalize_repo_id(repo_id)

    try:
        with get_session() as session:
            rows = (
                session.query(RepoChunk)
                .filter(RepoChunk.repo_id == repo_id)
                .all()
            )
    except Exception as e:
        logger.warning("repo_chunks table missing or DB error: %s", e)
        return []

    if not rows:
        return []

    texts = [r.text for r in rows]
    vocab = _build_vocab(texts)
    if not vocab:
        return []

    q_vec = _vectorize(query_text, vocab)

    scored = []
    for row in rows:
        c_vec = _vectorize(row.text, vocab)
        sim = _cosine(q_vec, c_vec)
        scored.append((sim, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {"file_path": r.file_path, "chunk_index": r.chunk_index, "text": r.text, "score": s}
        for s, r in scored[:top_k]
    ]


def chunk_file(content: str, file_path: str) -> list[dict]:
    chunks: list[dict] = []
    lines = content.splitlines(keepends=True)
    current_lines: list[str] = []
    current_len = 0
    chunk_index = 0

    for line in lines:
        line_len = len(line)
        if current_lines and current_len + line_len > CHUNK_SIZE_CHARS:
            text = "".join(current_lines)
            chunks.append({"text": text, "file_path": file_path, "chunk_index": chunk_index})
            chunk_index += 1
            overlap: list[str] = []
            overlap_len = 0
            for prev_line in reversed(current_lines):
                if overlap_len + len(prev_line) > CHUNK_OVERLAP_CHARS:
                    break
                overlap.insert(0, prev_line)
                overlap_len += len(prev_line)
            current_lines = overlap
            current_len = overlap_len
        current_lines.append(line)
        current_len += line_len

    if current_lines:
        text = "".join(current_lines)
        if text.strip():
            chunks.append({"text": text, "file_path": file_path, "chunk_index": chunk_index})

    return chunks


def embed_repo(repo_id: str, repo_url: str, repo_path: Path) -> int:
    from db import get_session
    from models import RepoChunk, Base, engine

    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        logger.warning("Could not ensure tables exist: %s", e)

    try:
        with get_session() as session:
            existing = session.query(RepoChunk).filter(RepoChunk.repo_id == repo_id).first()
            if existing:
                count = session.query(RepoChunk).filter(RepoChunk.repo_id == repo_id).count()
                logger.info("Repo %s already embedded (%d chunks), skipping", repo_id, count)
                return 0
    except Exception as e:
        logger.warning("Could not check existing chunks: %s", e)

    files = collect_scope_files(repo_path, ".")

    all_chunks: list[dict] = []
    for f in files:
        file_chunks = chunk_file(f["content"], f["path"])
        for c in file_chunks:
            c["repo_id"] = repo_id
        all_chunks.extend(file_chunks)

    if not all_chunks:
        logger.warning("No chunks produced for repo %s", repo_id)
        return 0

    try:
        with get_session() as session:
            session.query(RepoChunk).filter(RepoChunk.repo_id == repo_id).delete()
            for c in all_chunks:
                session.add(RepoChunk(
                    repo_id=repo_id,
                    file_path=c["file_path"],
                    chunk_index=c["chunk_index"],
                    text=c["text"],
                ))
    except Exception as e:
        logger.warning("Could not save chunks (table may not exist): %s", e)
        return 0

    logger.info("Embedded %d chunks for repo %s", len(all_chunks), repo_id)
    return len(all_chunks)
