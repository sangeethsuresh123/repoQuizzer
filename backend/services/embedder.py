"""
Chunking + embedding pipeline for the "Chat with the repo" RAG feature.

Design choice — single Chroma collection vs one per repo_id:
    Single collection with repo_id in metadata is preferred because:
    1. No dynamic collection creation / deletion to manage.
    2. Chroma filters by metadata efficiently (indexed alongside the HNSW graph).
    3. Leaves the door open for cross-repo search in the future.
"""

import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from config import CHROMA_PERSIST_DIR, CHROMA_HOST, CHROMA_PORT
from services.repo_service import collect_scope_files, slug_for_url

logger = logging.getLogger("repoquiz.embedder")

# ── Chunking constants ────────────────────────────────────────────────
CHUNK_SIZE_CHARS = 2000      # ~500 tokens (4 chars/token rough estimate)
CHUNK_OVERLAP_CHARS = 200    # ~50 tokens

# ── Lazy-loaded singletons ───────────────────────────────────────────
_model: SentenceTransformer | None = None
_chroma: chromadb.ClientAPI | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_chroma() -> chromadb.ClientAPI:
    global _chroma
    if _chroma is None:
        if CHROMA_HOST:
            logger.info("Connecting to Chroma server at %s:%s", CHROMA_HOST, CHROMA_PORT)
            _chroma = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        else:
            _chroma = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    return _chroma


# ── Chunking ──────────────────────────────────────────────────────────

def chunk_file(content: str, file_path: str) -> list[dict]:
    """Split *content* into overlapping chunks, breaking at line boundaries.

    Returns a list of {"text": ..., "file_path": ..., "chunk_index": ...} dicts.
    Chunks never cross file boundaries — each call produces chunks for one file only.
    """
    chunks: list[dict] = []
    lines = content.splitlines(keepends=True)
    current_lines: list[str] = []
    current_len = 0
    chunk_index = 0

    for line in lines:
        line_len = len(line)

        # If adding this line would exceed the target size, flush the chunk.
        if current_lines and current_len + line_len > CHUNK_SIZE_CHARS:
            text = "".join(current_lines)
            chunks.append({
                "text": text,
                "file_path": file_path,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

            # Keep trailing overlap lines for the next chunk.
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

    # Flush the remaining content.
    if current_lines:
        text = "".join(current_lines)
        if text.strip():  # skip blank trailing chunks
            chunks.append({
                "text": text,
                "file_path": file_path,
                "chunk_index": chunk_index,
            })

    return chunks


# ── Embedding pipeline ────────────────────────────────────────────────

def embed_repo(repo_id: str, repo_url: str, repo_path: Path) -> int:
    """Embed every code file in *repo_path* and upsert into Chroma.

    Returns the number of chunks created.  On failure the caller gets
    an exception — the /import handler catches and logs it but still
    returns the tree so the quiz flow is not blocked.
    """
    from db import get_session
    from models import RepoChunk

    # 1. Collect code files (reuses existing extension/size filtering).
    files = collect_scope_files(repo_path, ".")

    # 2. Chunk each file independently (no cross-file merging).
    all_chunks: list[dict] = []
    for f in files:
        file_chunks = chunk_file(f["content"], f["path"])
        for c in file_chunks:
            c["repo_id"] = repo_id
        all_chunks.extend(file_chunks)

    if not all_chunks:
        logger.warning("No chunks produced for repo %s", repo_id)
        return 0

    # 3. Embed all chunks in one batch call.
    model = _get_model()
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=False)

    # 4. Upsert into the single Chroma collection (filtered by repo_id metadata).
    chroma = _get_chroma()
    collection = chroma.get_or_create_collection(
        name="repo_chunks",
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"{repo_id}::{c['file_path']}::{c['chunk_index']}" for c in all_chunks]
    metadatas = [
        {"repo_id": repo_id, "file_path": c["file_path"], "chunk_index": c["chunk_index"]}
        for c in all_chunks
    ]

    # Delete any previously embedded chunks for this repo (re-embed support).
    existing = collection.get(where={"repo_id": repo_id})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=metadatas,
    )

    # 5. Sync chunk metadata to Postgres (for text retrieval / display).
    with get_session() as session:
        session.query(RepoChunk).filter(RepoChunk.repo_id == repo_id).delete()
        for i, c in enumerate(all_chunks):
            session.add(RepoChunk(
                repo_id=repo_id,
                file_path=c["file_path"],
                chunk_index=c["chunk_index"],
                text=c["text"],
                embedding_id=ids[i],
            ))

    logger.info("Embedded %d chunks for repo %s", len(all_chunks), repo_id)
    return len(all_chunks)
