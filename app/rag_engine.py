"""Deterministic business-rule RAG scoring engine.

The LLM is NOT used for scoring. All RAG calculations are rule-based.
"""

import statistics

from loguru import logger

from app.models import ParsedProject, RiskAssessment, DimensionScore
from app.config import RAG_WEIGHTS, RAG_THRESHOLDS
from app.utils import count_negative_sentiments


def _score_schedule_health(project: ParsedProject) -> DimensionScore:
    """Score based on Schedule Health column and task-level health flags."""
    healths = [t.schedule_health.lower() for t in project.tasks if t.schedule_health]
    if not healths:
        # Fallback: use summary
        summary_health = project.raw_summary.get("Schedule Health", "").lower()
        if summary_health == "red":
            return DimensionScore(name="Schedule Health", score=25, weight=RAG_WEIGHTS["schedule_health"],
                                  detail="Summary sheet declares Red schedule health.")
        elif summary_health in ("yellow", "amber"):
            return DimensionScore(name="Schedule Health", score=55, weight=RAG_WEIGHTS["schedule_health"],
                                  detail="Summary sheet declares Amber schedule health.")
        elif summary_health == "green":
            return DimensionScore(name="Schedule Health", score=85, weight=RAG_WEIGHTS["schedule_health"],
                                  detail="Summary sheet declares Green schedule health.")
        return DimensionScore(name="Schedule Health", score=50, weight=RAG_WEIGHTS["schedule_health"],
                              detail="No schedule health data available.", missing_data=True)

    red = healths.count("red")
    green = healths.count("green")
    yellow = healths.count("yellow") + healths.count("amber")
    total = len(healths)

    score = ((green * 100 + yellow * 60 + red * 20) / total) if total else 50
    score = max(0, min(100, score))
    detail = f"Schedule health indicators: {green} Green, {yellow} Amber/Yellow, {red} Red across {total} tasks."
    return DimensionScore(name="Schedule Health", score=round(score, 1), weight=RAG_WEIGHTS["schedule_health"],
                          detail=detail)


def _score_milestones(project: ParsedProject) -> DimensionScore:
    """Score based on milestone completion rates and overdues."""
    if not project.milestones:
        # Fallback: overall completion %
        pct = project.completion_percent
        if pct > 0:
            score = pct
            return DimensionScore(name="Milestones", score=round(score, 1), weight=RAG_WEIGHTS["milestones"],
                                  detail=f"Overall project completion at {pct:.0f}%.")
        return DimensionScore(name="Milestones", score=50, weight=RAG_WEIGHTS["milestones"],
                              detail="No milestone data available.", missing_data=True)

    pcts = [m.percent_complete for m in project.milestones]
    avg_pct = statistics.mean(pcts) if pcts else 0

    overdue = sum(1 for m in project.milestones if not m.completed and m.variance_days is not None and m.variance_days < 0)
    penalty = min(40, overdue * 10)
    score = max(0, avg_pct - penalty)

    detail = f"{len(project.milestones)} milestones tracked; avg completion {avg_pct:.0f}%."
    if overdue:
        detail += f" {overdue} milestone(s) overdue."
    return DimensionScore(name="Milestones", score=round(score, 1), weight=RAG_WEIGHTS["milestones"], detail=detail)


def _score_critical_tasks(project: ParsedProject) -> DimensionScore:
    """Score based on critical path tasks that are overdue or problematic."""
    critical_tasks = [t for t in project.tasks if t.critical]
    if not critical_tasks:
        return DimensionScore(name="Critical Tasks", score=85, weight=RAG_WEIGHTS["critical_tasks"],
                              detail="No critical path flags; defaulting to healthy.", missing_data=True)

    overdue = sum(1 for t in critical_tasks
                  if t.status.lower() not in ("completed", "done")
                  and t.variance_days is not None and t.variance_days < 0)

    at_risk = sum(1 for t in critical_tasks if t.at_risk)

    penalty = min(80, (overdue * 15 + at_risk * 10))
    score = max(0, 100 - penalty)

    parts = []
    if overdue:
        parts.append(f"{overdue} overdue")
    if at_risk:
        parts.append(f"{at_risk} at-risk")
    issues = ", ".join(parts) if parts else "no issues"
    detail = f"{len(critical_tasks)} critical path tasks; {issues}."
    return DimensionScore(name="Critical Tasks", score=round(score, 1), weight=RAG_WEIGHTS["critical_tasks"], detail=detail)


def _score_variance(project: ParsedProject) -> DimensionScore:
    """Score based on schedule variance across tasks."""
    variances = [t.variance_days for t in project.tasks if t.variance_days is not None]
    if not variances:
        return DimensionScore(name="Variance", score=50, weight=RAG_WEIGHTS["variance"],
                              detail="No variance data available.", missing_data=True)

    avg_var = statistics.mean(variances)
    total_behind = sum(1 for v in variances if v < -2)

    if avg_var <= -20:
        score = 10
        detail = f"Average variance {avg_var:.0f}d - severe slippage."
    elif avg_var <= -10:
        score = 30
        detail = f"Average variance {avg_var:.0f}d - significant slippage."
    elif avg_var <= -3:
        score = 55
        detail = f"Average variance {avg_var:.0f}d - moderate slippage."
    elif avg_var <= 2:
        score = 85
        detail = f"Average variance {avg_var:.0f}d - on track."
    else:
        score = 95
        detail = f"Average variance {avg_var:.0f}d - ahead of schedule."

    if total_behind > 5:
        penalty = min(30, total_behind * 3)
        score = max(0, score - penalty)
        detail += f" {total_behind} tasks behind schedule."
    return DimensionScore(name="Variance", score=round(score, 1), weight=RAG_WEIGHTS["variance"], detail=detail)


def _score_sentiment(project: ParsedProject) -> DimensionScore:
    """Score based on stakeholder sentiment in comments."""
    texts = [t.comments for t in project.tasks if t.comments]
    texts += [c.text for c in project.comments]
    texts = [t for t in texts if len(t) > 3]

    if not texts:
        return DimensionScore(name="Sentiment", score=50, weight=RAG_WEIGHTS["sentiment"],
                              detail="No stakeholder comments available; assumed neutral.", missing_data=True)

    neg_count = count_negative_sentiments(texts)
    ratio = neg_count / len(texts)

    score = max(0, 100 - (ratio * 150))
    if ratio > 0.4:
        detail = f"Negative sentiment in {neg_count}/{len(texts)} comments."
    elif ratio > 0.15:
        detail = f"Some concerns in {neg_count}/{len(texts)} comments."
    else:
        detail = f"Stakeholder sentiment appears positive ({neg_count}/{len(texts)} flagged)."
    return DimensionScore(name="Sentiment", score=round(score, 1), weight=RAG_WEIGHTS["sentiment"], detail=detail)


def assess(project: ParsedProject) -> RiskAssessment:
    """Run the full deterministic RAG assessment."""
    logger.info(f"Running RAG assessment for '{project.name}'")

    dims = [
        _score_schedule_health(project),
        _score_milestones(project),
        _score_critical_tasks(project),
        _score_variance(project),
        _score_sentiment(project),
    ]

    aggregate = sum(d.score * d.weight / 100 for d in dims)

    if aggregate >= RAG_THRESHOLDS["high"]:
        rag = "Green"
    elif aggregate >= RAG_THRESHOLDS["medium"]:
        rag = "Amber"
    else:
        rag = "Red"

    # Top reasons (sorted by contribution)
    sorted_dims = sorted(dims, key=lambda d: d.score * d.weight, reverse=True)
    top_reasons = []
    for d in sorted_dims:
        if d.score < 60:
            top_reasons.append(f"{d.name} ({d.score:.0f}/100): {d.detail[:80]}")
    if not top_reasons:
        top_reasons.append("All dimensions within acceptable range.")

    missing = [d.name for d in dims if d.missing_data]

    logger.info(f"RAG result: {rag} (score={aggregate:.1f})")
    return RiskAssessment(
        project_name=project.name,
        rag=rag,
        aggregate_score=round(aggregate, 1),
        dimensions=dims,
        top_reasons=top_reasons[:5],
        missing_data_flags=missing,
    )
