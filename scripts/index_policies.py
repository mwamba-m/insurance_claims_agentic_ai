from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import POLICY_DIR
from app.rag.chunking import chunk_policy_file
from app.rag.qdrant_store import index_chunks


def main() -> None:
    chunks = []
    for path in POLICY_DIR.glob("*.md"):
        chunks.extend(chunk_policy_file(path))
    count = index_chunks(chunks)
    print(f"Indexed {count} policy chunks into Qdrant")

if __name__ == "__main__":
    main()
