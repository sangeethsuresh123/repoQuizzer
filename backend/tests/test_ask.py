"""Tests for services.ask — RAG endpoint logic with mocked model + LLM."""

from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures / helpers ────────────────────────────────────────────────

def _fake_chroma_results(docs, metas, distances):
    """Return the dict shape that Chroma collection.query() produces."""
    return {
        "documents": [docs],
        "metadatas": [metas],
        "distances": [distances],
        "ids": [[]],
        "embeddings": None,
        "uris": None,
        "data": None,
    }


class _FakeNumpyArray:
    """Minimal stand-in so .tolist() works on the mock encode output."""
    def __init__(self, data):
        self._data = data
    def tolist(self):
        return self._data


def _mock_model():
    """Return a mock sentence-transformers model whose encode() returns a fixed vector."""
    m = MagicMock()
    m.encode.return_value = _FakeNumpyArray([[0.1] * 384])
    return m


def _mock_chroma(results):
    """Return a mock chromadb client whose collection.query() returns *results*."""
    collection = MagicMock()
    collection.query.return_value = results
    client = MagicMock()
    client.get_collection.return_value = collection
    return client


def _mock_llm_response(answer_text="The answer is 42."):
    """Return a mock OpenAI response object whose content is answer_text."""
    choice = MagicMock()
    choice.message.content = answer_text
    response = MagicMock()
    response.choices = [choice]
    return response


# ── Tests ─────────────────────────────────────────────────────────────

class TestAskRelevanceThreshold:
    """When Chroma returns no matches above threshold, /ask returns the
    'couldn't find anything relevant' response."""

    @patch("services.ask._get_chroma")
    @patch("services.ask._get_model")
    def test_no_matches_empty_chroma(self, mock_model_fn, mock_chroma_fn):
        mock_model_fn.return_value = _mock_model()
        mock_chroma_fn.return_value = _mock_chroma(
            _fake_chroma_results([], [], [])
        )

        from services.ask import ask
        result = ask("repo-abc", "What does init_db do?")

        assert "couldn't find anything relevant" in result["answer"]
        assert result["sources"] == []

    @patch("services.ask._get_chroma")
    @patch("services.ask._get_model")
    def test_weak_match_returns_not_relevant(self, mock_model_fn, mock_chroma_fn):
        """Distance > MAX_DISTANCE (0.7) → not relevant."""
        mock_model_fn.return_value = _mock_model()
        mock_chroma_fn.return_value = _mock_chroma(
            _fake_chroma_results(
                docs=["some random code"],
                metas=[{"repo_id": "repo-abc", "file_path": "x.py", "chunk_index": 0}],
                distances=[0.9],  # above 0.7 threshold
            )
        )

        from services.ask import ask
        result = ask("repo-abc", "What does init_db do?")

        assert "couldn't find anything relevant" in result["answer"]
        assert result["sources"] == []


class TestAskGoodMatch:
    """When Chroma returns relevant chunks and the LLM is configured,
    /ask returns a properly shaped answer + sources object."""

    @patch("services.ask._client", None)
    @patch("services.ask._get_chroma")
    @patch("services.ask._get_model")
    def test_no_llm_returns_sources(self, mock_model_fn, mock_chroma_fn):
        """LLM client is None → answer says LLM not configured, sources still returned."""
        mock_model_fn.return_value = _mock_model()
        mock_chroma_fn.return_value = _mock_chroma(
            _fake_chroma_results(
                docs=["def init_db():\n    pass"],
                metas=[{"repo_id": "repo-abc", "file_path": "db.py", "chunk_index": 0}],
                distances=[0.3],  # well within threshold
            )
        )

        from services.ask import ask
        result = ask("repo-abc", "How does the database get initialized?")

        assert "not configured" in result["answer"]
        assert len(result["sources"]) == 1
        assert result["sources"][0] == "db.py"

    @patch("services.ask._client")
    @patch("services.ask._get_chroma")
    @patch("services.ask._get_model")
    def test_good_match_returns_answer_and_sources(
        self, mock_model_fn, mock_chroma_fn, mock_client
    ):
        mock_model_fn.return_value = _mock_model()
        mock_chroma_fn.return_value = _mock_chroma(
            _fake_chroma_results(
                docs=[
                    "def init_db():\n    Base.metadata.create_all()",
                    "engine = create_engine(DATABASE_URL)",
                ],
                metas=[
                    {"repo_id": "repo-abc", "file_path": "db.py", "chunk_index": 0},
                    {"repo_id": "repo-abc", "file_path": "db.py", "chunk_index": 1},
                ],
                distances=[0.2, 0.35],
            )
        )
        mock_client.chat.completions.create.return_value = _mock_llm_response(
            "The database is initialized in db.py using SQLAlchemy's create_all()."
        )

        from services.ask import ask
        result = ask("repo-abc", "How does the database get initialized?")

        assert "create_all" in result["answer"]
        # Both chunks are from db.py — deduplicated to one entry.
        assert len(result["sources"]) == 1
        assert result["sources"][0] == "db.py"
        # LLM was called once.
        mock_client.chat.completions.create.assert_called_once()

    @patch("services.ask._client")
    @patch("services.ask._get_chroma")
    @patch("services.ask._get_model")
    def test_llm_exception_returns_graceful_error(
        self, mock_model_fn, mock_chroma_fn, mock_client
    ):
        """If the LLM call raises, /ask returns an error message + sources."""
        mock_model_fn.return_value = _mock_model()
        mock_chroma_fn.return_value = _mock_chroma(
            _fake_chroma_results(
                docs=["code here"],
                metas=[{"repo_id": "repo-abc", "file_path": "x.py", "chunk_index": 0}],
                distances=[0.1],
            )
        )
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")

        from services.ask import ask
        result = ask("repo-abc", "What is this?")

        assert "unavailable" in result["answer"]
        assert len(result["sources"]) == 1  # sources still returned
