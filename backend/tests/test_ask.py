"""Tests for services.ask — RAG endpoint logic with TF-IDF retrieval."""

from unittest.mock import patch

import pytest


# ── Helpers ────────────────────────────────────────────────────────────

def _mock_search_results(results):
    """Return a fake search_chunks function that returns *results*."""
    def _search(repo_id, query_text, top_k=5):
        return results
    return _search


def _mock_llm_response(answer_text="The answer is 42."):
    """Return a mock OpenAI response object whose content is answer_text."""
    choice = MagicMock()
    choice.message.content = answer_text
    response = MagicMock()
    response.choices = [choice]
    return response


# ── Tests ─────────────────────────────────────────────────────────────

from unittest.mock import MagicMock


class TestAskRelevanceThreshold:
    """When search returns no chunks above threshold, /ask returns the
    'couldn't find anything relevant' response."""

    @patch("services.ask.search_chunks")
    def test_no_chunks(self, mock_search):
        mock_search.return_value = []

        from services.ask import ask
        result = ask("repo-abc", "What does init_db do?")

        assert "couldn't find anything relevant" in result["answer"]
        assert result["sources"] == []

    @patch("services.ask.search_chunks")
    def test_weak_match_below_threshold(self, mock_search):
        mock_search.return_value = [
            {"file_path": "x.py", "chunk_index": 0, "text": "some code", "score": 0.1},
        ]

        from services.ask import ask
        result = ask("repo-abc", "What does init_db do?")

        assert "couldn't find anything relevant" in result["answer"]
        assert result["sources"] == []


class TestAskGoodMatch:
    """When search returns relevant chunks and the LLM is configured,
    /ask returns a properly shaped answer + sources object."""

    @patch("services.ask._client", None)
    @patch("services.ask.search_chunks")
    def test_no_llm_returns_sources(self, mock_search):
        mock_search.return_value = [
            {"file_path": "db.py", "chunk_index": 0, "text": "def init_db(): pass", "score": 0.8},
        ]

        from services.ask import ask
        result = ask("repo-abc", "How does the database get initialized?")

        assert "not configured" in result["answer"]
        assert len(result["sources"]) == 1
        assert result["sources"][0] == "db.py"

    @patch("services.ask._client")
    @patch("services.ask.search_chunks")
    def test_good_match_returns_answer_and_sources(self, mock_search, mock_client):
        mock_search.return_value = [
            {"file_path": "db.py", "chunk_index": 0, "text": "def init_db(): Base.metadata.create_all()", "score": 0.9},
            {"file_path": "db.py", "chunk_index": 1, "text": "engine = create_engine(DATABASE_URL)", "score": 0.7},
        ]
        mock_client.chat.completions.create.return_value = _mock_llm_response(
            "The database is initialized in db.py using SQLAlchemy's create_all()."
        )

        from services.ask import ask
        result = ask("repo-abc", "How does the database get initialized?")

        assert "create_all" in result["answer"]
        assert len(result["sources"]) == 1
        assert result["sources"][0] == "db.py"
        mock_client.chat.completions.create.assert_called_once()

    @patch("services.ask._client")
    @patch("services.ask.search_chunks")
    def test_llm_exception_returns_graceful_error(self, mock_search, mock_client):
        mock_search.return_value = [
            {"file_path": "x.py", "chunk_index": 0, "text": "code here", "score": 0.8},
        ]
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")

        from services.ask import ask
        result = ask("repo-abc", "What is this?")

        assert "unavailable" in result["answer"]
        assert len(result["sources"]) == 1
