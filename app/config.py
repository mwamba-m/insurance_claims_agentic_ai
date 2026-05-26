from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
CLAIMS_FILE = DATA_DIR / "claims" / "synthetic_claims.jsonl"
DOCUMENTS_FILE = DATA_DIR / "documents" / "synthetic_documents.jsonl"
POLICY_DIR = DATA_DIR / "policies"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
USE_GROQ = os.getenv("USE_GROQ", "true").lower() == "true" and bool(GROQ_API_KEY)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant") #"llama-3.3-70b-versatile")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "policy_chunks")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "384"))

LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "claims-agentic-ai-mvp")
