from __future__ import annotations

import hashlib
import math
import re
from app.config import VECTOR_SIZE

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")

class HashingEmbedder:
    """Dependency-light deterministic embeddings for local MVP testing.

    This avoids heavy ML wheels while you test Python 3.14.x. Replace with
    sentence-transformers later if your environment supports it.
    """

    def __init__(self, dim: int = VECTOR_SIZE):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self.dim
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]
