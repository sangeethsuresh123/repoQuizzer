# repo-quiz

A repository-aware quiz generator for code comprehension. Paste a public GitHub repo,
pick a file or folder scope, and get a short quiz (3 MCQs + one coding task) generated
straight from that code, with explanations and locally saved history.

After completing a round, you can generate **more questions** from the same scope (the
LLM is instructed to avoid repeats) or **finish** to see a session summary with
personalised improvement feedback.

## Stack

- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind
- **Backend:** FastAPI (Python)
- **Repo ingestion:** `git clone --depth 1` of the target repo
- **Question generation & grading:** `meta-llama/llama-3.3-70b-instruct` via
  [OpenRouter](https://openrouter.ai) (OpenAI-compatible endpoint, `openai` Python SDK)
- **Storage:** SQLite (`backend/storage/quiz_history.db`)

## How it works

1. **Import** — backend shallow-clones the repo URL into `backend/storage/repos/`
   and walks the tree, filtering to recognised code file extensions.
2. **Scope** — the frontend renders that tree; the user picks one file or one folder.
3. **Generate** — backend reads every code file in the scope (capped in size), builds
   one text blob with file markers, and prompts the LLM to return strict JSON: 3 MCQs
   plus one coding task (bug-fix or write-snippet), each with an explanation.
4. **Take the quiz** — MCQs render as diff-style option lines; the coding task is a
   plain textarea seeded with starter code.
5. **Grade** — MCQs are graded by exact index match. The coding answer is graded by
   asking the LLM to compare it against a reference solution for correctness (not
   exact text match).
6. **More rounds** — after grading, the user can request more questions from the same
   scope. Previous question text is sent to the LLM so it generates *different*
   questions each round.
7. **Finish** — when done, a session summary shows overall score, per-round breakdown,
   every missed question with its explanation, and personalised feedback on areas
   to improve.
8. **History** — every attempt (quiz, answers, score) is saved to SQLite and listed
   on `/history` as a commit-log style timeline you can expand.

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- `git` on PATH (used for cloning repos)
- An [OpenRouter](https://openrouter.ai) API key

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
NVIDIA_API_KEY=sk-or-v1-...          # your OpenRouter API key
NVIDIA_BASE_URL=https://openrouter.ai/api/v1
LLAMA_MODEL=meta-llama/llama-3.3-70b-instruct
```

Start the server:

```bash
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`. The frontend calls the backend at
`http://localhost:8000` by default — override with `NEXT_PUBLIC_API_BASE` in a
`frontend/.env.local` if you run the backend elsewhere.

## Deployment

The frontend and backend are **separate services** — the frontend is a static
Next.js app (hostable on Vercel, Netlify, etc.) and the backend is a Python API
(hostable on Railway, Render, Fly.io, a VPS, etc.). They communicate over HTTP,
so they just need to be able to reach each other.

### Frontend (Vercel)

1. Push this repo to GitHub.
2. In the [Vercel dashboard](https://vercel.com), import the repo.
3. Set **Root Directory** to `frontend`.
4. Vercel auto-detects Next.js — the build settings should be correct.
5. Go to **Settings → Environment Variables** and add:

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | `https://your-backend-url` |

6. Deploy. Vercel builds a static Next.js site with client-side routing
   (the `vercel.json` rewrite handles SPA fallback).

### Frontend (Netlify)

1. In the [Netlify dashboard](https://netlify.com), import the repo.
2. Set **Base directory** to `frontend`.
3. Set **Build command** to `npm install && npm run build`.
4. Set **Publish directory** to `.next`.
5. Go to **Site settings → Environment variables** and add:

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | `https://your-backend-url` |

6. Deploy. The `netlify.toml` at the repo root handles SPA redirect fallback.

### Backend

The backend is a standard Python/FastAPI app. Any host that supports Python
will work:

- **Railway** — add a service from this repo, set the root directory to `backend`,
  and add the env vars from `backend/.env`.
- **Render** — create a "Web Service", point to this repo, set root directory
  to `backend`, build command to `pip install -r requirements.txt`, and start
  command to `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- **Fly.io** — write a `Dockerfile` for the backend directory.

Make sure `git` is available in the deployment environment (the backend clones
repos at runtime). Also note that SQLite storage is ephemeral on most cloud
hosts — quiz history will be lost on redeploy. For persistent storage, swap
`db.py` to use PostgreSQL or a hosted SQLite service.

### Environment variable summary

| Where | Variable | Example |
|---|---|---|
| Backend `.env` | `NVIDIA_API_KEY` | `sk-or-v1-...` |
| Backend `.env` | `NVIDIA_BASE_URL` | `https://openrouter.ai/api/v1` |
| Backend `.env` | `LLAMA_MODEL` | `meta-llama/llama-3.3-70b-instruct` |
| Frontend (deploy host) | `NEXT_PUBLIC_API_BASE` | `https://your-backend.onrender.com` |

## Features

| Feature | Description |
|---|---|
| **Repo import** | Shallow-clones any public GitHub repo and renders a navigable file tree |
| **Scope selection** | Pick a single file or an entire directory as the quiz scope |
| **AI-generated quizzes** | 3 code-specific MCQs + 1 coding task, generated from the actual source |
| **Diff-style UI** | GitHub-dark theme with diff-line markers for correct/wrong answers |
| **Coding task grading** | LLM-judged correctness against a reference solution |
| **Multiple rounds** | Generate new questions from the same scope without re-importing |
| **Previous-question exclusion** | The LLM is told which questions were already asked so it picks new ones |
| **Session summary** | Score breakdown, missed-question review, and improvement feedback |
| **Quiz history** | All attempts saved to SQLite, browsable with expand/collapse detail |
| **Fallback quiz** | If the LLM is unavailable, a regex-based fallback generates basic structural questions |

## Configuration

Key environment variables in `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `NVIDIA_API_KEY` | *(required)* | OpenRouter API key |
| `NVIDIA_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible API base |
| `LLAMA_MODEL` | `meta-llama/llama-3.3-70b-instruct` | Model to use for generation and grading |

Backend hard limits (in `main.py` / `quiz_generator.py`):

| Constant | Value | Purpose |
|---|---|---|
| `GENERATE_TOTAL_TIMEOUT` | 200s | Hard cap on the entire generate endpoint |
| `QUIZ_TIMEOUT_SECONDS` | 150s | Timeout for the LLM quiz generation call |
| `GRADING_TIMEOUT_SECONDS` | 120s | Timeout for the LLM coding grading call |
| `MAX_FILE_BYTES` | 60 KB | Skip individual files larger than this |
| `MAX_TOTAL_CHUNK_CHARS` | 10,000 | Cap on combined code sent to the LLM per quiz |

## Project structure

```
repoQuizzer/
├── backend/
│   ├── main.py                 # FastAPI routes + async orchestration
│   ├── config.py               # Env vars, paths, limits
│   ├── db.py                   # SQLite init + queries
│   ├── requirements.txt
│   ├── .env                    # API keys and model config
│   ├── services/
│   │   ├── repo_service.py     # Clone, tree building, file collection
│   │   ├── chunker.py          # Builds the code context blob
│   │   ├── quiz_generator.py   # LLM quiz generation + fallback
│   │   └── grader.py           # MCQ grading (pure) + LLM coding grading
│   └── storage/
│       ├── repos/              # Cloned repos
│       └── quiz_history.db     # SQLite database
└── frontend/
    ├── app/
    │   ├── layout.tsx          # Root layout with nav header
    │   ├── page.tsx            # Home — repo import + file tree picker
    │   ├── quiz/page.tsx       # Quiz: generate → take → grade → summary
    │   └── history/page.tsx    # Past attempts with expand/collapse
    ├── components/
    │   └── FileTree.tsx        # Recursive file tree component
    └── lib/
        ├── api.ts              # Fetch wrapper with timeout
        └── types.ts            # TypeScript type definitions
```

## Notes / limitations

- Only public GitHub repos, cloned shallow (`--depth 1`) — no auth, no private repos.
- Individual files over ~60 KB are skipped; total code sent to the LLM per quiz is
  capped (~10K chars) so quizzes stay fast and cheap to generate.
- No user accounts — history is local to whoever's machine is running the backend.
- Coding-task grading is LLM-judged, not sandboxed code execution — it's checking
  reasoning/correctness against a reference solution, not running tests.
- OpenRouter free-tier requests may take 10-45s depending on load; timeouts are set
  generously to accommodate this.

## Possible extensions

- Sandbox-execute the coding answer against real test cases instead of LLM judging.
- Difficulty levels, or letting the user pick MCQ count.
- Export quiz history, or a leaderboard if this became multi-user.
- Support private repos via GitHub token authentication.
- Adaptive difficulty based on per-topic performance across rounds.
