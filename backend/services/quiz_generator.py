import json
import re
from openai import OpenAI

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, LLAMA_MODEL

_client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY) if NVIDIA_API_KEY else None


class QuizGenerationError(Exception):
    pass


QUIZ_SYSTEM_PROMPT = """You are a senior engineer writing a short code-comprehension quiz \
about a specific slice of a real codebase. Base every question strictly on the provided \
source code — never invent behavior that isn't in the code. Questions should test whether \
someone actually read and understood this code (control flow, data structures, edge cases, \
what a function returns, why a bug exists), not generic language trivia.

Respond with ONLY valid JSON. No markdown fences, no commentary, no text before or after the \
JSON object. The JSON must match exactly this shape:

{
  "mcqs": [
    {
      "id": "q1",
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "correct_index": 0,
      "explanation": "string, why the correct answer is correct and others are wrong"
    }
  ],
  "coding_task": {
    "type": "bug_fix",
    "title": "string",
    "prompt": "string describing exactly what the user must write or fix",
    "starter_code": "string, code the user edits",
    "reference_solution": "string, a correct solution",
    "explanation": "string, why the reference solution is correct"
  }
}

Rules:
- Generate exactly 3 mcqs. Exactly one coding_task.
- Keep every code snippet under 15 lines.
- Inside JSON strings, write newlines as \\n and escape any double quotes as \\".
- Do not wrap the JSON in markdown code fences.
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _extract_json(text: str) -> dict:
    """Small models are inconsistent about pure JSON output, so this tries a few
    increasingly forgiving strategies before giving up."""
    text = _strip_fences(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find the widest {...} span and parse that.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # common small-model mistake: trailing commas before ] or }
            fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                raise QuizGenerationError(
                    f"Model did not return parseable JSON even after cleanup: {e}"
                )

    raise QuizGenerationError("Model response contained no JSON object.")


def generate_quiz(scope_path: str, context_blob: str) -> dict:
    if _client is None:
        raise QuizGenerationError(
            "NVIDIA_API_KEY is not set on the backend. Add it to backend/.env."
        )

    user_prompt = (
        f"Scope: {scope_path}\n\n"
        f"Here is the source code for this scope:\n{context_blob}\n\n"
        "Generate the quiz JSON now. Output ONLY the JSON object."
    )

    response = _client.chat.completions.create(
        model=LLAMA_MODEL,
        temperature=0.2,
        top_p=0.7,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_text = response.choices[0].message.content or ""
    quiz = _extract_json(raw_text)

    if "mcqs" not in quiz or "coding_task" not in quiz or not quiz["mcqs"]:
        raise QuizGenerationError(
            "Model response was missing required quiz fields — try regenerating, "
            "small models occasionally drop a field."
        )
    return quiz
