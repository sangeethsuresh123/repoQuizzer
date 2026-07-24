# repoQuizzer

A repository-aware quiz generator for code comprehension. Paste a public GitHub repo,
pick a file or folder scope, and get a short quiz (3 MCQs + one coding task) generated
straight from that code, with explanations and locally saved history.

After completing a round, you can generate **more questions** from the same scope (the
LLM is instructed to avoid repeats) or **finish** to see a session summary with
personalised improvement feedback.

### Live Demo

- **Frontend:** [repo-quizzer.vercel.app](https://repo-quizzer2.vercel.app/)
- **Backend API:** [repoquizzer.onrender.com](https://repoquizzer.onrender.com)

## Stack

- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Backend:** FastAPI (Python 3.12)
- **Repo ingestion:** `git clone --depth 1` of the target repo
- **Question generation & grading:** `meta-llama/llama-3.3-70b-instruct` via
  [OpenRouter](https://openrouter.ai) (OpenAI-compatible endpoint, `openai` Python SDK)
- **Tech detection:** Static analysis of file extensions + manifest files
- **Dependency graph:** Regex-based import/require/use parsing with force-directed SVG visualization
- **Storage:** PostgreSQL via SQLAlchemy + Alembic migrations (SQLite fallback for local dev)

## How it works

1. **Import** — backend shallow-clones the repo, walks the file tree, detects technologies
   (languages, frameworks, tools) and builds a dependency graph between files.
2. **Explore** — the frontend renders an interactive force-directed dependency graph
   alongside a file tree. Click a node or file to select it as the quiz scope.
3. **Generate** — backend reads every code file in the scope (capped in size), builds
   one text blob with file markers, and prompts the LLM to return strict JSON: 3 MCQs
   plus one coding task, each with an explanation.
4. **Take the quiz** — MCQs render as diff-style option lines; the coding task is a
   plain textarea seeded with starter code.
5. **Grade** — MCQs are graded by exact index match. The coding answer is graded by
   asking the LLM to compare it against a reference solution.
6. **More rounds** — after grading, the user can request more questions from the same
   scope. Previous question text is sent to the LLM so it generates *different*
   questions each round.
7. **Finish** — when done, a session summary shows overall score, per-round breakdown,
   every missed question with its explanation, and personalised feedback.
8. **History** — every attempt (quiz, answers, score) is saved to PostgreSQL and listed
   on `/history` as a commit-log style timeline you can expand.

## Features

| Feature | Description |
|---|---|
| **Repo import** | Shallow-clones any public GitHub repo and renders a navigable file tree |
| **Technology detection** | Identifies languages, frameworks, and tools from code files and manifests, with tutorial links |
| **Dependency graph** | Interactive SVG force-directed graph showing import relationships between files |
| **Scope selection** | Pick a file from the graph, the file tree, or a directory |
| **AI-generated quizzes** | 3 code-specific MCQs + 1 coding task, generated from the actual source |
| **Diff-style UI** | GitHub-dark theme with diff-line markers for correct/wrong answers |
| **Coding task grading** | LLM-judged correctness against a reference solution |
| **Multiple rounds** | Generate new questions from the same scope without re-importing |
| **Previous-question exclusion** | The LLM is told which questions were already asked so it picks new ones |
| **Session summary** | Score breakdown, missed-question review, and improvement feedback |
| **Quiz history** | All attempts saved to PostgreSQL, browsable with expand/collapse detail |
| **Fallback quiz** | If the LLM is unavailable, a regex-based fallback generates basic structural questions |

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- `git` on PATH (used for cloning repos)
- An [OpenRouter](https://openrouter.ai) API key

### Quick start (Docker Compose)

```bash
cp backend/.env.example backend/.env   # paste your NVIDIA_API_KEY
docker compose up --build
```

This starts two containers:
- **postgres** — `localhost:5432` (healthchecked, persistent volume)
- **backend** — `localhost:8000` (runs Alembic migration then uvicorn)

Then start the frontend:

```bash
cd frontend && npm install && npm run dev
```

### Manual setup

#### Backend

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
alembic upgrade head      # create/migrate tables
uvicorn main:app --reload --port 8000
```

#### Frontend

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
(hostable on Railway, Render, Fly.io, a VPS, etc.). They communicate over HTTP.

### Frontend (Vercel)

1. Push this repo to GitHub.
2. In the [Vercel dashboard](https://vercel.com), import the repo.
3. Set **Root Directory** to `frontend`.
4. Go to **Settings → Environment Variables** and add:

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | `https://repoquizzer.onrender.com` |

5. Deploy.

### Backend

The backend is a standard Python/FastAPI app. Any host that supports Python
will work:

- **Render** — create a "Web Service", point to this repo, set the root directory
  to `backend`. The Dockerfile installs `git` and runs `alembic upgrade head` on
  startup.
- **Docker Compose** — run `docker compose up --build` (see Quick start above).
- **Railway** — add a service from this repo, set root directory to `backend`,
  and add the env vars from `backend/.env`.

Make sure `git` is available in the deployment environment (the backend clones
repos at runtime). Set `DATABASE_URL` to a Postgres connection string for
persistent storage in production.

### Environment variable summary

| Where | Variable | Example |
|---|---|---|
| Backend | `NVIDIA_API_KEY` | `sk-or-v1-...` |
| Backend | `NVIDIA_BASE_URL` | `https://openrouter.ai/api/v1` |
| Backend | `LLAMA_MODEL` | `meta-llama/llama-3.3-70b-instruct` |
| Backend (deploy) | `DATABASE_URL` | `postgresql://user:pass@host:5432/db` |
| Frontend (deploy) | `NEXT_PUBLIC_API_BASE` | `https://repoquizzer.onrender.com` |

## Configuration

Backend hard limits (in `config.py` / `main.py`):

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
├── docker-compose.yml          # Local dev: postgres + backend
├── backend/
│   ├── main.py                 # FastAPI routes + async orchestration
│   ├── config.py               # Env vars, paths, limits
│   ├── models.py               # SQLAlchemy ORM models (Repo, Attempt)
│   ├── db.py                   # SQLAlchemy session-based queries
│   ├── alembic.ini             # Alembic config
│   ├── alembic/                # Database migrations
│   ├── Dockerfile              # Python 3.12-slim + git for cloning
│   ├── requirements.txt
│   ├── .env                    # API keys and model config
│   ├── .env.example            # Documents all env vars
│   ├── services/
│   │   ├── repo_service.py     # Clone, tree building, file collection
│   │   ├── chunker.py          # Builds the code context blob
│   │   ├── tech_detector.py    # Language/framework/tool detection + tutorial links
│   │   ├── dep_graph.py        # Import parsing + dependency graph building
│   │   ├── quiz_generator.py   # LLM quiz generation + fallback
│   │   └── grader.py           # MCQ grading (pure) + LLM coding grading
│   └── storage/
│       └── repos/              # Cloned repos
└── frontend/
    ├── app/
    │   ├── layout.tsx          # Root layout with nav header
    │   ├── page.tsx            # Home — import, tech badges, graph, file tree
    │   ├── quiz/page.tsx       # Quiz: generate → take → grade → summary
    │   └── history/page.tsx    # Past attempts with expand/collapse
    ├── components/
    │   ├── FileTree.tsx        # Recursive file tree component
    │   └── DependencyGraph.tsx # Interactive SVG force-directed dependency graph
    └── lib/
        ├── api.ts              # Fetch wrapper with timeout
        └── types.ts            # TypeScript type definitions
```

## Notes / limitations

- Only public GitHub repos, cloned shallow (`--depth 1`) — no auth, no private repos.
- Individual files over ~60 KB are skipped; total code sent to the LLM per quiz is
  capped (~10K chars) so quizzes stay fast and cheap to generate.
- No user accounts — quiz history is shared per database instance.
- Coding-task grading is LLM-judged, not sandboxed code execution.
- The dependency graph handles Python, JS/TS/JSX/TSX, Go, Rust, and Java import patterns.
  Third-party/stdlib imports are filtered out to keep the graph clean.
- The graph caps at 60 nodes for large repos, keeping the most connected files.
- OpenRouter free-tier requests may take 10-45s; timeouts are set generously.

## Possible extensions

- Sandbox-execute the coding answer against real test cases instead of LLM judging.
- Difficulty levels, or letting the user pick MCQ count.
- Export quiz history, or a leaderboard if this became multi-user.
- Support private repos via GitHub token authentication.
- Adaptive difficulty based on per-topic performance across rounds.
- Support for more languages in the dependency graph (PHP, Ruby, Swift, Kotlin, etc.).
