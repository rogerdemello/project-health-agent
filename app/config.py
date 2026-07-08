"""Application configuration via environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", ROOT / "outputs"))
LOGS_DIR = ROOT / "logs"
PROMPTS_DIR = ROOT / "prompts"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# --- LLM: NVIDIA NIM (OpenAI-compatible endpoint) ---
# The narration LLM speaks the OpenAI wire format, so we use the `openai` SDK
# pointed at NVIDIA NIM's base URL. OPENAI_API_KEY is still honored as a fallback
# so the same code runs against OpenAI directly if preferred.
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

LLM_API_KEY = NVIDIA_API_KEY or os.getenv("OPENAI_API_KEY", "").strip()
# NVIDIA key → use NIM base URL; otherwise fall back to OpenAI's default endpoint.
LLM_BASE_URL = NVIDIA_BASE_URL if NVIDIA_API_KEY else os.getenv("OPENAI_BASE_URL", "")
# Default to llama-3.1-8b-instruct on NIM: it stays warm on the serverless free
# tier and responds in ~1-2s. Larger models (e.g. meta/llama-3.3-70b-instruct)
# give higher quality but can cold-start for minutes on the free tier — point
# LLM_MODEL at one if your tier keeps it warm.
LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "meta/llama-3.1-8b-instruct" if NVIDIA_API_KEY else "gpt-4o-mini",
)

# Backward-compatible aliases (older imports referenced these names).
OPENAI_API_KEY = LLM_API_KEY
OPENAI_MODEL = LLM_MODEL

# RAG weights (must sum to 100)
RAG_WEIGHTS: dict[str, float] = {
    "schedule_health": 30.0,
    "milestones": 25.0,
    "critical_tasks": 20.0,
    "variance": 15.0,
    "sentiment": 10.0,
}

RAG_THRESHOLDS = {
    "high": 85.0,
    "medium": 60.0,
    # below 60 = Red
}

# Column name aliases for fuzzy matching
COLUMN_ALIASES: dict[str, list[str]] = {
    "task_name": ["task name", "task", "activity", "name"],
    "status": ["status", "task status", "activity status"],
    "percent_complete": ["% complete", "percent complete", "complete", "completion %", "pct complete"],
    "start_date": ["start date", "start", "begin date", "start_date"],
    "end_date": ["end date", "end", "finish date", "finish", "end_date"],
    "baseline_start": ["baseline start", "baseline start date", "baseline_start"],
    "baseline_finish": ["baseline finish", "baseline end date", "baseline finish date", "baseline_finish"],
    "variance": ["variance", "var", "schedule variance"],
    "schedule_health": ["schedule health", "health", "rag", "status indicator"],
    "critical": ["critical ?", "critical", "critical path", "is critical"],
    "owner": ["owner", "resource", "assigned to", "resource name"],
    "comments": ["comments", "comment", "notes", "remarks", "status comment"],
    "phase": ["phase/milestone", "phase", "milestone", "phase milestone"],
    "at_risk": ["at risk?", "at risk", "risk flag", "is at risk"],
    "on_hold": ["on hold?", "on hold", "hold"],
}
