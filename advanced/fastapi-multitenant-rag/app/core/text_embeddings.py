import hashlib
import json
import math
import re

_EMBED_DIM = 128
_CHUNK_SIZE = 420
_CHUNK_OVERLAP = 80


def chunk_text(
    text: str,
    *,
    max_chars: int = _CHUNK_SIZE,
    overlap: int = _CHUNK_OVERLAP,
) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        chunks.append(normalized[start:end])
        if end >= len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def embed_text(text: str, *, dimensions: int = _EMBED_DIM) -> list[float]:
    """Deterministic pseudo-embedding for demos (not an ML model)."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    counter = 0
    while len(values) < dimensions:
        block = hashlib.sha256(digest + counter.to_bytes(4, "big")).digest()
        counter += 1
        for i in range(0, len(block), 4):
            if len(values) >= dimensions:
                break
            chunk = int.from_bytes(block[i : i + 4], "big", signed=False)
            values.append((chunk / 2**32) * 2 - 1)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


def embedding_to_json(vector: list[float]) -> str:
    return json.dumps(vector, separators=(",", ":"))


def embedding_from_json(raw: str) -> list[float]:
    data = json.loads(raw)
    if not isinstance(data, list):
        msg = "Invalid embedding payload"
        raise ValueError(msg)
    return [float(x) for x in data]
