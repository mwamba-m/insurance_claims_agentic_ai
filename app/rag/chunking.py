from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SECTION_RE = re.compile(r"^##\s+(?P<section>.+)$", re.MULTILINE)


def chunk_policy_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    product_type = "motor" if "motor" in path.name.lower() else "home"
    chunks: list[dict[str, Any]] = []
    parts = SECTION_RE.split(text)
    preamble = parts[0]
    pairs = list(zip(parts[1::2], parts[2::2]))
    for section, body in pairs:
        paras = [p.strip() for p in body.split("\n\n") if p.strip()]
        current = ""
        chunk_no = 0
        for para in paras:
            if len(current) + len(para) > 1200 and current:
                chunks.append(_make_chunk(path, product_type, section, current, chunk_no))
                chunk_no += 1
                current = para
            else:
                current = (current + "\n\n" + para).strip()
        if current:
            chunks.append(_make_chunk(path, product_type, section, current, chunk_no))
    if not chunks and preamble.strip():
        chunks.append(_make_chunk(path, product_type, "General", preamble.strip(), 0))
    return chunks


def _make_chunk(path: Path, product_type: str, section: str, text: str, chunk_no: int) -> dict[str, Any]:
    clause_type = "general"
    low = text.lower()
    if "exclusion" in low or "not cover" in low or "will not cover" in low:
        clause_type = "exclusion"
    elif "excess" in low:
        clause_type = "excess"
    elif "condition" in low or "must" in low:
        clause_type = "condition"
    elif "cover" in low:
        clause_type = "coverage"
    return {
        "id": f"{path.stem}_{section.lower().replace(' ', '_')}_{chunk_no}",
        "text": text,
        "metadata": {
            "source_file": path.name,
            "product_type": product_type,
            "section": section,
            "clause_type": clause_type,
            "chunk_no": chunk_no,
        },
    }
