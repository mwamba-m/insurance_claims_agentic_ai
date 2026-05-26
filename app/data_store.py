from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from app.config import CLAIMS_FILE, DOCUMENTS_FILE


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def get_claim(claim_id: str) -> dict[str, Any] | None:
    for row in _read_jsonl(CLAIMS_FILE):
        if row.get("claim_id") == claim_id:
            return row
    return None


def list_claims(limit: int = 20) -> list[dict[str, Any]]:
    return _read_jsonl(CLAIMS_FILE)[:limit]


def get_documents_for_claim(claim_id: str) -> list[dict[str, Any]]:
    return [d for d in _read_jsonl(DOCUMENTS_FILE) if d.get("claim_id") == claim_id]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
