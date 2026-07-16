"""
RAG-based "Chat with the repo" — embed a question, retrieve top code
chunks from Chroma, and ask the LLM to answer grounded in that context.
"""

import logging

from services.embedder import _get_model, _get_chroma
from services.quiz_generator import _client  # reuse existing OpenAI client
from config import LLAMA_MODEL

logger = logging.getLogger("repoquiz.ask")

# Cosine distance threshold (Chroma metric: 1 − cosine_similarity).
# 0.7 ≈ cosine similarity 0.3 — below this the chunks are considered
# weakly relevant and we tell the user we couldn't find anything useful.
MAX_DISTANCE = 0.7

TOP_K = 5

ASK_SYSTEM_PROMPT = """\
You are a helpful assistant that answers questions about a codebase. \
You are given retrieved code chunks from the repository. Answer the \
user's question **only** using the provided code context.

Rules:
1. If the provided code chunks are not relevant to the question, respond \
with exactly: "I couldn't find anything relevant in this repository for \
that question."
2. When you answer, cite which file(s) you used by referencing the \
[FILE: ...] header in the context.
3. Be concise — 1-4 sentences unless the user asks for more detail.
4. Do not invent code or behaviour that is not present in the chunks.
"""


def ask(repo_id: str, question: str) -> dict:
    """Embed *question*, retrieve top chunks, call LLM, return answer + sources."""

    # 1. Embed the question with the same model used for indexing.
    model = _get_model()
    q_embedding = model.encode([question]).tolist()

    # 2. Similarity search in Chroma, filtered to this repo.
    chroma = _get_chroma()
    collection = chroma.get_collection("repo_chunks")

    results = collection.query(
        query_embeddings=q_embedding,
        n_results=TOP_K,
        where={"repo_id": repo_id},
        include=["documents", "metadatas", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    # 3. Check relevance — if the closest chunk is too far away, say so.
    if not docs or distances[0] > MAX_DISTANCE:
        return {
            "answer": "I couldn't find anything relevant in this repository for that question.",
            "sources": [],
        }

    # 4. Build the context block for the LLM.
    context_parts: list[str] = []
    sources: list[dict] = []
    for doc, meta, dist in zip(docs, metas, distances):
        header = f"[FILE: {meta['file_path']} | chunk {meta['chunk_index']}]"
        context_parts.append(f"{header}\n{doc}")
        snippet = doc[:200].replace("\n", " ").strip()
        sources.append({
            "file_path": meta["file_path"],
            "chunk_index": meta["chunk_index"],
            "snippet": snippet,
        })

    context_block = "\n\n---\n\n".join(context_parts)

    user_prompt = (
        f"Code context:\n\n{context_block}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the code context above. Cite file(s) you used."
    )

    # 5. Call the LLM.
    if _client is None:
        return {
            "answer": "LLM is not configured on the backend. Cannot generate an answer.",
            "sources": sources,
        }

    try:
        response = _client.chat.completions.create(
            model=LLAMA_MODEL,
            temperature=0.2,
            top_p=0.7,
            max_tokens=500,
            messages=[
                {"role": "system", "content": ASK_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = response.choices[0].message.content or "No response from the LLM."
    except Exception as e:
        logger.error("LLM call failed in /ask: %s", e)
        answer = (
            "The LLM service is currently unavailable. "
            "Please try again later."
        )

    return {"answer": answer, "sources": sources}
