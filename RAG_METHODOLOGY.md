# RAG Status Methodology for Project Health Reporting

## Overview
The RAG (Red/Amber/Green) status is determined by evaluating **five weighted
dimensions** derived from the project plan data. Each dimension is scored 0–100
by **deterministic business rules** (never the LLM). The weighted aggregate maps
to the final RAG status.

> Scoring is implemented in `app/rag_engine.py`; weights and thresholds live in
> `app/config.py`. This document is kept in sync with that code.

## Dimensions & Weighting

| Dimension | Weight | Data Sources |
|---|---|---|
| Schedule Health | 30% | Task-level `Schedule Health` flags (Green/Yellow/Amber/Red); falls back to the Summary sheet |
| Milestones | 25% | Milestone completion %, overdue milestones; falls back to overall project completion % |
| Critical Tasks | 20% | Overdue and at-risk critical-path tasks (`Critical?` flag) |
| Variance | 15% | Average schedule variance (days) across tasks, count of tasks behind schedule |
| Sentiment | 10% | Negative-keyword frequency in task comments and the Comments sheet |

Weights sum to 100 (`RAG_WEIGHTS` in `app/config.py`).

## Scoring Logic

Each dimension returns a `DimensionScore` in the range 0–100.

### Schedule Health (30%)
Per-task health flags are pooled and weighted:
`score = (green·100 + amber/yellow·60 + red·20) / total_flagged_tasks`.
If no task-level flags exist, the Summary sheet's `Schedule Health` value is used
(Red → 25, Amber/Yellow → 55, Green → 85); if that is also absent, neutral 50.

### Milestones (25%)
`score = avg_milestone_completion% − overdue_penalty`, where
`overdue_penalty = min(40, overdue_count · 10)`.
A milestone is overdue when it is incomplete and its variance is negative.
If no milestones are detected, overall project completion % is used as a fallback.

### Critical Tasks (20%)
`score = max(0, 100 − penalty)` where
`penalty = min(80, overdue·15 + at_risk·10)`.
Only critical-path tasks that are not yet completed contribute. If no critical
tasks are flagged, the dimension defaults to a healthy 85.

### Variance (15%)
Banded on the **average** task variance (days):

| Avg variance | Base score | Interpretation |
|---|---|---|
| ≤ −20 | 10 | Severe slippage |
| ≤ −10 | 30 | Significant slippage |
| ≤ −3 | 55 | Moderate slippage |
| ≤ +2 | 85 | On track |
| > +2 | 95 | Ahead of schedule |

If more than 5 tasks are behind schedule (variance < −2), an additional
`min(30, behind_count · 3)` penalty is subtracted.

### Stakeholder Sentiment (10%)
`score = max(0, 100 − negative_ratio · 150)`, where `negative_ratio` is the
fraction of comments containing a negative keyword (e.g. *delay, blocked,
concern, sign-off pending, at risk, overdue, escalate* — see
`count_negative_sentiments` in `app/utils.py`). If there are no comments, the
dimension defaults to neutral 50.

## Aggregate & RAG Thresholds

`aggregate = Σ (dimension_score · weight / 100)`

| Aggregate Score | RAG Status |
|---|---|
| ≥ 85 | Green |
| 60 – 84 | Amber |
| < 60 | Red |

Thresholds are `RAG_THRESHOLDS` in `app/config.py`.

## Handling Missing / Messy Data

| Scenario | Behavior |
|---|---|
| Missing dates | Task excluded from variance; parsed via multiple formats |
| Missing completion % | Assumed 0% |
| Missing schedule-health flags | Falls back to Summary sheet, then neutral (50) |
| No milestones | Falls back to overall completion % |
| No critical-path flags | Defaults to healthy (85) |
| No comments | Sentiment scored neutral (50) |
| `#UNPARSEABLE` / blank / `N/A` variance | Treated as 0 |
| Invalid cells | Logged as a warning and skipped gracefully |

Every dimension carries a `missing_data` flag so downstream reports and the LLM
explanation can disclose which inputs were unavailable.

## Assumptions
1. Budget/cost data is not present in the source plans, so no explicit budget
   dimension is scored; schedule and completion metrics act as the health proxy.
2. Stakeholder sentiment is inferred from free-text comments in the Comments
   sheet and per-task comment fields.
3. The `Critical?` flag identifies critical-path tasks; only incomplete ones are
   penalized.
4. The assessment date is taken from the Summary sheet when available, otherwise
   the system date.
5. A task at 100% complete but past its baseline finish is treated as done and is
   not penalized for variance.
6. Missing data in a dimension defaults to neutral (50) rather than 0, to avoid
   false alarms.
7. Schedule variance is expressed in days; negative values mean behind schedule.
