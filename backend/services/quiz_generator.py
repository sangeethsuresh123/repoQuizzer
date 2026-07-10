import json
import re
from openai import OpenAI

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, LLAMA_MODEL

_client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY, timeout=150.0) if NVIDIA_API_KEY else None

QUIZ_TIMEOUT_SECONDS = 150


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


def generate_quiz(scope_path: str, context_blob: str, previous_questions: list[str] | None = None) -> dict:
    if _client is None:
        raise QuizGenerationError(
            "NVIDIA_API_KEY is not set on the backend. Add it to backend/.env."
        )

    user_prompt = (
        f"Scope: {scope_path}\n\n"
        f"Here is the source code for this scope:\n{context_blob}\n\n"
    )

    if previous_questions:
        prev_list = "\n".join(f"- {q}" for q in previous_questions)
        user_prompt += (
            f"The following questions have ALREADY been asked — do NOT repeat them "
            f"or ask similar questions. Generate completely different questions:\n"
            f"{prev_list}\n\n"
        )

    user_prompt += "Generate the quiz JSON now. Output ONLY the JSON object."

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

    try:
        quiz = _extract_json(raw_text)
    except QuizGenerationError:
        with open("/tmp/quiz_raw.txt", "w") as f:
            f.write(raw_text)
        raise

    if "mcqs" not in quiz or "coding_task" not in quiz or not quiz["mcqs"]:
        raise QuizGenerationError(
            "Model response was missing required quiz fields — try regenerating, "
            "small models occasionally drop a field."
        )
    return quiz


def generate_fallback_quiz(scope_path: str, files: list[dict]) -> dict:
    """Generate a basic quiz from code structure when the LLM is unavailable."""
    all_code = "\n".join(f["content"] for f in files)
    lines = all_code.splitlines()

    funcs = re.findall(r"(?:def|function|fn)\s+(\w+)", all_code)
    classes = re.findall(r"class\s+(\w+)", all_code)
    imports = re.findall(r"(?:^|\n)(?:import|from)\s+([\w.]+)", all_code)
    strings = re.findall(r'"([^"]{5,80})"', all_code)
    comments = re.findall(r"#\s*(.+)", all_code)

    names = [c for c in classes if len(c) > 2][:5] or [f for f in funcs if len(f) > 2][:5] or ["module"]

    code_sample_lines = [l for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*"))]
    code_sample = "\n".join(code_sample_lines[:15]) if code_sample_lines else "# No code found"

    mcqs = []
    if names:
        mcqs.append({
            "id": "q1",
            "question": f"What is the name of this class or function defined in {scope_path or 'the code'}?",
            "options": [
                names[0],
                names[0] + "_test",
                "main",
                "init",
            ],
            "correct_index": 0,
            "explanation": f"The identifier '{names[0]}' is defined in the source code under {scope_path}.",
        })
    if len(funcs) >= 2:
        mcqs.append({
            "id": "q2",
            "question": f"Which of these functions is defined in {scope_path or 'the code'}?",
            "options": [
                funcs[0],
                "print_this",
                "run_tests",
                "setup_config",
            ],
            "correct_index": 0,
            "explanation": f"'{funcs[0]}' is defined in the source. The other options do not appear.",
        })
    else:
        mcqs.append({
            "id": "q2",
            "question": f"Based on the code in {scope_path or 'the repo'}, which statement is true?",
            "options": [
                f"The code contains {len(lines)} lines",
                "The code has no functions",
                "The code is only comments",
                "The code is empty",
            ],
            "correct_index": 0,
            "explanation": f"The code file(s) contain approximately {len(lines)} lines total.",
        })

    mcqs.append({
        "id": "q3",
        "question": f"What type of content does {scope_path or 'this scope'} primarily contain?",
        "options": [
            "Source code",
            "Configuration only",
            "Documentation only",
            "Test data",
        ],
        "correct_index": 0,
        "explanation": f"This scope contains source code files with {len(files)} file(s).",
    })

    starter_lines = code_sample_lines[:10]
    starter = "\n".join(starter_lines) if starter_lines else "# starter code"
    ref = code_sample_lines[:12]
    ref_solution = "\n".join(ref) if ref else starter

    coding_task = {
        "type": "bug_fix",
        "title": f"Understand the code in {scope_path or 'this scope'}",
        "prompt": f"Review the following code from {scope_path} and add a docstring to the main function or class.",
        "starter_code": starter,
        "reference_solution": ref_solution,
        "explanation": "This is a code comprehension exercise based on the actual source files in the selected scope.",
    }

    return {"mcqs": mcqs, "coding_task": coding_task}
