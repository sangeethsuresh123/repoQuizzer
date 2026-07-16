# repoQuizzer

A repository-aware quiz generator for code comprehension. Paste a public GitHub repo,
pick a file or folder scope, and get a short quiz (3 MCQs + one coding task) generated
straight from that code, with explanations and locally saved history.

After completing a round, you can generate **more questions** from the same scope (the
LLM is instructed to avoid repeats) or **finish** to see a session summary with
personalised improvement feedback.

### Live Demo

- **Frontend:** [repoquizzer.vercel.app](https://repo-quizzer-3zuw.vercel.app/)
- **Backend API:** [repoquizzer.onrender.com](https://repoquizzer.onrender.com)

## Stack

- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind
- **Backend:** FastAPI (Python)
- **Repo ingestion:** `git clone --depth 1` of the target repo
- **Question generation & grading:** `meta-llama/llama-3.3-70b-instruct` via
  [OpenRouter](https://openrouter.ai) (OpenAI-compatible endpoint, `openai` Python SDK)
- **RAG embeddings:** `all-MiniLM-L6-v2` via
  [sentence-transformers](https://www.sbert.net/) (runs locally, no embeddings API key needed)
- **Vector store:** [ChromaDB](https://www.trychroma.com/) (persistent, HTTP client/server mode in Docker)
- **Storage:** PostgreSQL via SQLAlchemy + Alembic migrations (SQLite fallback for local dev)

## How it works

1. **Import** — backend shallow-clones the repo URL into `backend/storage/repos/`,
   walks the tree, filtering to recognised code file extensions, then chunks every
   file and stores the embeddings in ChromaDB for later retrieval.
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
8. **Chat with the repo** — after importing, users can ask free-form questions about
   the codebase. The backend embeds the question, runs a similarity search against
   the stored chunks, and feeds the top 5 results as context to the LLM for an
   answer with file citations.
9. **History** — every attempt (quiz, answers, score) is saved to PostgreSQL and listed
   on `/history` as a commit-log style timeline you can expand.

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- `git` on PATH (used for cloning repos)
- An [OpenRouter](https://openrouter.ai) API key

### Quick start (Docker Compose)

The fastest way to get the full stack running locally — PostgreSQL, ChromaDB, and
the FastAPI backend — in one command:

```bash
cp backend/.env.example backend/.env   # paste your NVIDIA_API_KEY
docker compose up --build
```

This starts three containers:
- **postgres** — `localhost:5432` (healthchecked, persistent volume)
- **chroma** — internal only, backend connects via service name
- **backend** — `localhost:8000` (runs Alembic migration then uvicorn)

Then start the frontend as usual:

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
   | `NEXT_PUBLIC_API_BASE` | `https://repoquizzer.onrender.com` |

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

- **Docker Compose** — run `docker compose up --build` (see Quick start above). This
  brings up Postgres, ChromaDB, and the backend with persistent volumes.
- **Railway** — add a service from this repo, set the root directory to `backend`,
  and add the env vars from `backend/.env`.
- **Render** — create a "Web Service", point to this repo, set root directory
  to `backend`, build command to `pip install -r requirements.txt`, and start
  command to `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`.
- **Fly.io** — write a `Dockerfile` for the backend directory.

Make sure `git` is available in the deployment environment (the backend clones
repos at runtime). Set `DATABASE_URL` to a Postgres connection string for
persistent storage in production.

### Environment variable summary

| Where | Variable | Example |
|---|---|---|
| Backend `.env` | `NVIDIA_API_KEY` | `sk-or-v1-...` |
| Backend `.env` | `NVIDIA_BASE_URL` | `https://openrouter.ai/api/v1` |
| Backend `.env` | `LLAMA_MODEL` | `meta-llama/llama-3.3-70b-instruct` |
| Backend (deploy host) | `DATABASE_URL` | `postgresql://user:pass@host:5432/db` |
| Backend (Docker) | `CHROMA_HOST` | `chroma` |
| Backend (Docker) | `CHROMA_PORT` | `8000` |
| Frontend (deploy host) | `NEXT_PUBLIC_API_BASE` | `https://repoquizzer.onrender.com` |

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
| **Chat with the repo** | Ask free-form questions about the codebase; answered via RAG with file citations |
| **Quiz history** | All attempts saved to PostgreSQL, browsable with expand/collapse detail |
| **Fallback quiz** | If the LLM is unavailable, a regex-based fallback generates basic structural questions |

## Configuration

Key environment variables in `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `NVIDIA_API_KEY` | *(required)* | OpenRouter API key |
| `NVIDIA_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible API base |
| `LLAMA_MODEL` | `meta-llama/llama-3.3-70b-instruct` | Model to use for generation and grading |
| `DATABASE_URL` | `sqlite:///...` | Postgres URL for production; omit for local SQLite |
| `CHROMA_HOST` | *(empty — local mode)* | Set to use Chroma HTTP server (e.g. `chroma` in Docker Compose) |
| `CHROMA_PORT` | `8000` | Chroma HTTP port (only used when `CHROMA_HOST` is set) |

Backend hard limits (in `main.py` / `quiz_generator.py`):

| Constant | Value | Purpose |
|---|---|---|
| `GENERATE_TOTAL_TIMEOUT` | 200s | Hard cap on the entire generate endpoint |
| `QUIZ_TIMEOUT_SECONDS` | 150s | Timeout for the LLM quiz generation call |
| `GRADING_TIMEOUT_SECONDS` | 120s | Timeout for the LLM coding grading call |
| `MAX_FILE_BYTES` | 60 KB | Skip individual files larger than this |
| `MAX_TOTAL_CHUNK_CHARS` | 10,000 | Cap on combined code sent to the LLM per quiz |

### RAG — Chat with the repo

After importing a repo, embeddings are generated for every code file and stored in
ChromaDB (single collection, filtered by `repo_id` metadata). The `/ask` endpoint
runs a full RAG pipeline:

1. Embed the user's question with `all-MiniLM-L6-v2` (local, ~200ms).
2. Query ChromaDB for the 5 most similar chunks (`MAX_DISTANCE = 0.7` cosine).
3. Build a context blob with `file_path` headers for each chunk.
4. Send context + question to the LLM and return the answer with source citations.

```bash
curl -X POST https://repoquizzer.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"repo_id": "my-repo-abc123def456", "question": "What does the authenticate function do?"}'
```

Response:

```json
{
  "answer": "The authenticate function verifies user credentials...",
  "sources": ["auth.py", "middleware.py"]
}
```

## Project structure

```
repoQuizzer/
├── docker-compose.yml          # Local dev: postgres + chroma + backend
├── backend/
│   ├── main.py                 # FastAPI routes + async orchestration
│   ├── config.py               # Env vars, paths, limits
│   ├── models.py               # SQLAlchemy ORM models (Repo, Attempt, RepoChunk)
│   ├── db.py                   # SQLAlchemy session-based queries
│   ├── alembic.ini             # Alembic config
│   ├── alembic/                # Database migrations
│   │   ├── env.py
│   │   └── versions/
│   ├── Dockerfile              # Python 3.12-slim + git for cloning
│   ├── requirements.txt
│   ├── .env                    # API keys and model config
│   ├── .env.example            # Documents all env vars
│   ├── services/
│   │   ├── repo_service.py     # Clone, tree building, file collection
│   │   ├── chunker.py          # Builds the code context blob
│   │   ├── embedder.py         # Chunking + sentence-transformers + Chroma storage
│   │   ├── ask.py              # RAG pipeline: embed question → Chroma → LLM answer
│   │   ├── quiz_generator.py   # LLM quiz generation + fallback
│   │   └── grader.py           # MCQ grading (pure) + LLM coding grading
│   ├── tests/
│   │   ├── test_embedder.py    # Chunking unit tests
│   │   └── test_ask.py         # RAG pipeline unit tests (mocked Chroma + LLM)
│   └── storage/
│       └── repos/              # Cloned repos
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
- No user accounts — quiz history is shared per database instance (Postgres in production, local SQLite for dev).
- Coding-task grading is LLM-judged, not sandboxed code execution — it's checking
  reasoning/correctness against a reference solution, not running tests.
- RAG uses a local embedding model (`all-MiniLM-L6-v2`, 384-dim) — no embeddings
  API key required. The model is downloaded on first use and cached by `sentence-transformers`.
- ChromaDB stores vectors on disk (local mode) or via HTTP (Docker mode). No
  external vector service is needed.
- OpenRouter free-tier requests may take 10-45s depending on load; timeouts are set
  generously to accommodate this.

## Possible extensions

- Sandbox-execute the coding answer against real test cases instead of LLM judging.
- Difficulty levels, or letting the user pick MCQ count.
- Export quiz history, or a leaderboard if this became multi-user.
- Support private repos via GitHub token authentication.
- Adaptive difficulty based on per-topic performance across rounds.
- Cross-repo search — query across multiple imported repos at once.
- Chat UI in the frontend to interact with the `/ask` endpoint conversationally.
