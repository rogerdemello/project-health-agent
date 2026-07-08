"""Shared utility functions."""

import re
import logging
from datetime import datetime, date
from pathlib import Path
from loguru import logger


def parse_date(val) -> date | None:
    """Safely parse a date from various formats."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, (int, float)):
        return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_variance(val) -> float | None:
    """Parse variance string like '-6d', '0', '1d' to float days."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s in ("#UNPARSEABLE", "", "?", "0", "N/A"):
        return 0.0
    m = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*d(?:ays?)?$", s, re.IGNORECASE)
    if m:
        return float(m.group(1))
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_percent(val) -> float:
    """Parse a percentage value to 0-100 float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        pct = float(val)
        return pct * 100 if pct <= 1 else min(pct, 100.0)
    s = str(val).strip().replace("%", "")
    try:
        pct = float(s)
        return pct * 100 if pct <= 1 else min(pct, 100.0)
    except (ValueError, TypeError):
        return 0.0


def count_negative_sentiments(texts: list[str]) -> int:
    """Count texts containing negative keywords indicating stakeholder concerns."""
    keywords = [
        "sign-off pending", "sign off pending", "yet to recieve sign off",
        "delay", "delayed", "blocked", "blocker", "concern", "concerns",
        "at risk", "pending", "stuck", "issue", "issues", "problem",
        "not started", "behind", "overdue", "escalate", "escalation",
    ]
    negatives = 0
    for t in texts:
        if t:
            lower = str(t).lower()
            for kw in keywords:
                if kw in lower:
                    negatives += 1
                    break
    return negatives


def ensure_dirs():
    """Create required directories."""
    from app.config import OUTPUT_DIR, LOGS_DIR
    for d in (OUTPUT_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def setup_logging():
    """Configure loguru."""
    from app.config import LOG_LEVEL, LOGS_DIR
    ensure_dirs()
    logger.remove()
    logger.add(
        LOGS_DIR / "agent.log",
        rotation="10 MB",
        retention=3,
        level=LOG_LEVEL,
    )
    logger.add(lambda msg: print(msg, end=""), level=LOG_LEVEL, colorize=True)
