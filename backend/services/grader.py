import json
import re
from openai import OpenAI

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, LLAMA_MODEL

_client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY) if NVIDIA_API_KEY else None

CODE_GRADER_SYSTEM_PROMPT = """You grade one code-writing/bug-fix answer against a reference \
solution. Judge correctness and reasoning, not exact text match — different but correct \
solutions should pass. Respond with ONLY valid JSON, no markdown fences, no commentary: \
{"correct": true, "feedback": "string, 1-3 sentences explaining the verdict"}"""


def grade_mcqs(mcqs: list[dict], answers: dict) -> list[dict]:
    """answers: {question_id: selected_index}. Returns per-question results."""
    results = []
    for q in mcqs:
        qid = q["id"]
        selected = answers.get(qid)
        is_correct = selected is not None and int(selected) == int(q["correct_index"])
        results.append({
            "id": qid,
            "selected_index": selected,
            "correct_index": q["correct_index"],
            "is_correct": is_correct,
            "explanation": q["explanation"],
        })
    return results


def _parse_grader_json(raw_text: str) -> dict:
    text = re.sub(r"^```(json)?|```$", "", raw_text.strip()).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    # Last resort: a small model sometimes just says "correct" or "incorrect" in prose.
    lowered = text.lower()
    if "true" in lowered or "correct" in lowered and "incorrect" not in lowered:
        return {"correct": True, "feedback": text[:300]}
    return {"correct": False, "feedback": text[:300] or "Could not parse grader response."}


def grade_coding_task(coding_task: dict, user_answer: str) -> dict:
    if not user_answer.strip():
        return {"correct": False, "feedback": "No answer was submitted."}

    if _client is None:
        # Fallback without an API key: naive non-empty check so the app still runs end to end.
        return {
            "correct": None,
            "feedback": "Automatic grading needs NVIDIA_API_KEY; compare your answer with the "
                         "reference solution shown in the explanation.",
        }

    prompt = (
        f"Task: {coding_task['prompt']}\n\n"
        f"Starter code:\n{coding_task['starter_code']}\n\n"
        f"Reference solution:\n{coding_task['reference_solution']}\n\n"
        f"User's answer:\n{user_answer}\n\n"
        "Grade the user's answer now. Output ONLY the JSON object."
    )
    response = _client.chat.completions.create(
        model=LLAMA_MODEL,
        temperature=0.1,
        top_p=0.7,
        max_tokens=300,
        messages=[
            {"role": "system", "content": CODE_GRADER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    raw_text = response.choices[0].message.content or ""
    return _parse_grader_json(raw_text)
