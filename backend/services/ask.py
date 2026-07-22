"""
RAG-based "Chat with the repo" — retrieve top code chunks via TF-IDF
similarity and ask the LLM to answer grounded in that context.
"""

import logging

from services.embedder import search_chunks
from services.quiz_generator import _client
from config import LLAMA_MODEL

logger = logging.getLogger("repoquiz.ask")

MIN_SCORE = 0.05
TOP_K = 5

ASK_SYSTEM_PROMPT = """\
You are a helpful assistant that answers questions about a codebase. \
You are given retrieved code chunks from the repository. Answer the \
user's question **only** using the provided code context.

Rules:
1. If the provided code chunks are not relevant to the question, respond \
with exactly: "I couldn't find anything relevant in this repository for \
that question."
2. When you answer, cite which file(s) you used.
3. Be concise — 1-4 sentences unless the user asks for more detail.
4. Do not invent code or behaviour that is not present in the chunks.
"""


def ask(repo_id: str, question: str) -> dict:
    results = search_chunks(repo_id, question, top_k=TOP_K)

    if not results or results[0]["score"] < MIN_SCORE:
        return {
            "answer": "I couldn't find anything relevant in this repository for that question.",
            "sources": [],
        }

    context_parts: list[str] = []
    source_files: list[str] = []
    seen_files: set[str] = set()
    for r in results:
        header = f"[FILE: {r['file_path']} | chunk {r['chunk_index']}]"
        context_parts.append(f"{header}\n{r['text']}")
        if r["file_path"] not in seen_files:
            source_files.append(r["file_path"])
            seen_files.add(r["file_path"])

    context_block = "\n\n---\n\n".join(context_parts)

    user_prompt = (
        f"Code context:\n\n{context_block}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the code context above. Cite file(s) you used."
    )

    if _client is None:
        return {
            "answer": "LLM is not configured on the backend. Cannot generate an answer.",
            "sources": source_files,
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
        answer = "The LLM service is currently unavailable. Please try again later."

    return {"answer": answer, "sources": source_files}
