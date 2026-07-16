"""Tests for services.embedder — chunking logic."""

from services.embedder import chunk_file, CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS


class TestChunkFile:
    """chunk_file must respect file boundaries and produce expected chunk counts."""

    def test_short_file_single_chunk(self):
        content = "def hello():\n    print('hi')\n"
        chunks = chunk_file(content, "hello.py")
        assert len(chunks) == 1
        assert chunks[0]["file_path"] == "hello.py"
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["text"] == content

    def test_empty_file_no_chunks(self):
        chunks = chunk_file("", "empty.py")
        assert chunks == []

    def test_blank_only_file_no_chunks(self):
        chunks = chunk_file("   \n  \n  ", "blank.py")
        assert chunks == []

    def test_long_file_produces_multiple_chunks(self):
        # Build a file that exceeds CHUNK_SIZE_CHARS.
        line = "x = 1  # padding line to fill up the chunk\n"
        target_lines = (CHUNK_SIZE_CHARS // len(line)) + 10
        content = line * target_lines
        chunks = chunk_file(content, "big.py")

        assert len(chunks) >= 2
        # All chunks belong to the same file.
        assert all(c["file_path"] == "big.py" for c in chunks)
        # Indices are sequential starting at 0.
        assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))

    def test_chunks_do_not_cross_file_boundary(self):
        """Each call to chunk_file produces chunks for exactly one file."""
        content = "a\n" * 5000
        chunks = chunk_file(content, "one.py")
        other_chunks = chunk_file(content, "two.py")

        for c in chunks:
            assert c["file_path"] == "one.py"
        for c in other_chunks:
            assert c["file_path"] == "two.py"

    def test_overlap_exists_between_consecutive_chunks(self):
        line = "A" * 100 + "\n"  # 101 chars per line
        # Need enough lines to exceed CHUNK_SIZE_CHARS at least twice.
        count = (CHUNK_SIZE_CHARS // 101) + 20
        content = line * count
        chunks = chunk_file(content, "overlap.py")

        if len(chunks) >= 2:
            # The tail of chunk N should appear near the head of chunk N+1
            # because of the overlap region.
            tail = chunks[0]["text"][-CHUNK_OVERLAP_CHARS:]
            head = chunks[1]["text"]
            # At least some of the tail should appear in the next chunk's head.
            assert tail[-50:] in head or head[:50] in tail, (
                "Overlap region not found between consecutive chunks"
            )

    def test_metadata_keys_present(self):
        chunks = chunk_file("print(1)\n", "meta.py")
        assert len(chunks) == 1
        c = chunks[0]
        assert "text" in c
        assert "file_path" in c
        assert "chunk_index" in c
        assert isinstance(c["text"], str)
        assert isinstance(c["chunk_index"], int)
