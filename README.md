# repo-quiz

A repository-aware quiz generator for code comprehension. Paste a public GitHub repo,
pick a file or folder scope, and get a short quiz (3-5 MCQs + one bug-fix/write-code
task) generated straight from that code, with explanations and locally saved history.

## Stack

- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind
- **Backend:** FastAPI (Python)
- **Repo ingestion:** `git clone --depth 1` of the target repo
- **Question generation & grading:** `meta/llama-3.2-1b-instruct` via NVIDIA's build.nvidia.com
  API catalog (OpenAI-compatible endpoint, `openai` Python SDK pointed at
  `https://integrate.api.nvidia.com/v1`)
- **Storage:** SQLite (`backend/storage/quiz_history.db`)

> **Model note:** Llama 3.2 1B is a small, low-latency model, not a heavyweight reasoner.
> Expect it to write more generic questions and occasionally malformed JSON compared to a
> larger model — `quiz_generator.py` has extra JSON-repair fallbacks to compensate, and the
> quiz is capped at exactly 3 MCQs for reliability. If quiz quality is too thin for your
> demo, swap `LLAMA_MODEL` in `.env` to `meta/llama-3.1-8b-instruct` or
> `meta/llama-3.1-70b-instruct` — same free catalog, no code changes needed.

## How it works

1. **Import** — backend shallow-clones the repo URL into `backend/storage/repos/`
   and walks the tree, filtering to recognized code file extensions.
2. **Scope** — the frontend renders that tree; the user picks one file or one folder.
3. **Generate** — backend reads every code file in the scope (capped in size), builds
   one text blob with file markers, and prompts Claude to return strict JSON: 3-5 MCQs
   plus one coding task (bug-fix or write-snippet), each with an explanation.
4. **Take the quiz** — MCQs render as diff-style option lines; the coding task is a
   plain textarea seeded with starter code.
5. **Grade** — MCQs are graded by exact index match. The coding answer is graded by
   asking Claude to compare it against a reference solution for correctness (not
   exact text match).
6. **History** — every attempt (quiz, answers, score) is saved to SQLite and listed
   on `/history` as a commit-log style timeline you can expand.

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then paste your NVIDIA_API_KEY into .env
uvicorn main:app --reload --port 8000
```

Get an API key at [build.nvidia.com](https://build.nvidia.com/meta/llama-3.2-1b-instruct) —
open the model page, click "Get API Key" next to the Python example, generate one (starts
with `nvapi-`), and paste it into `backend/.env`.

Requires `git` to be installed and on PATH (used for cloning repos).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`. The frontend calls the backend at
`http://localhost:8000` by default — override with `NEXT_PUBLIC_API_BASE` in a
`frontend/.env.local` if you run the backend elsewhere.

## Notes / limitations (by design, to keep this a small portfolio project)

- Only public GitHub repos, cloned shallow (`--depth 1`) — no auth, no private repos.
- Individual files over ~60KB are skipped; total code sent to the LLM per quiz is
  capped (~24K chars) so quizzes stay fast and cheap to generate.
- No user accounts — history is local to whoever's machine is running the backend.
- Coding-task grading is LLM-judged, not sandboxed code execution — it's checking
  reasoning/correctness against a reference solution, not literally running tests.

## Possible extensions

- Sandbox-execute the coding answer against real test cases instead of LLM judging.
- Difficulty levels, or letting the user pick MCQ count.
- Multi-file scopes (currently one file or one folder at a time).
- Export quiz history, or a leaderboard if this became multi-user.
