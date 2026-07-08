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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
