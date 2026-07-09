from config import MAX_TOTAL_CHUNK_CHARS


def build_context_blob(files: list[dict]) -> str:
    """Concatenate scope files into one budgeted text blob with clear file markers,
    so the model can cite specific files/lines in questions and explanations."""
    parts = []
    used = 0
    for f in files:
        header = f"\n\n===== FILE: {f['path']} ({f['language']}) =====\n"
        remaining = MAX_TOTAL_CHUNK_CHARS - used - len(header)
        if remaining <= 200:
            break
        content = f["content"]
        if len(content) > remaining:
            content = content[:remaining] + "\n... (truncated)"
        parts.append(header + content)
        used += len(header) + len(content)
        if used >= MAX_TOTAL_CHUNK_CHARS:
            break
    return "".join(parts)
