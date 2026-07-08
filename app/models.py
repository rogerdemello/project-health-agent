"""Pydantic v2 data models for project health reporting."""

from datetime import date, datetime
from pydantic import BaseModel, Field


class Comment(BaseModel):
    author: str = ""
    date: str = ""
    text: str = ""


class Task(BaseModel):
    id: int = 0
    name: str = ""
    owner: str = ""
    status: str = ""
    percent_complete: float = 0.0
    start_date: date | None = None
    end_date: date | None = None
    baseline_start: date | None = None
    baseline_finish: date | None = None
    variance_days: float | None = None
    critical: bool = False
    schedule_health: str = ""
    phase: str = ""
    at_risk: bool = False
    on_hold: bool = False
    comments: str = ""


class Milestone(BaseModel):
    name: str = ""
    due_date: date | None = None
    actual_date: date | None = None
    completed: bool = False
    percent_complete: float = 0.0
    variance_days: float | None = None


class ParsedProject(BaseModel):
    name: str = ""
    manager: str = ""
    start_date: date | None = None
    end_date: date | None = None
    completion_percent: float = 0.0
    status: str = ""
    tasks: list[Task] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)
    assessment_date: date | None = None
    raw_summary: dict[str, str] = Field(default_factory=dict)


class DimensionScore(BaseModel):
    name: str
    score: float = 0.0
    weight: float = 0.0
    detail: str = ""
    missing_data: bool = False


class RiskAssessment(BaseModel):
    project_name: str = ""
    rag: str = ""
    aggregate_score: float = 0.0
    dimensions: list[DimensionScore] = Field(default_factory=list)
    top_reasons: list[str] = Field(default_factory=list)
    missing_data_flags: list[str] = Field(default_factory=list)


class LLMExplanation(BaseModel):
    summary: str = ""
    reasons: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class WeeklyReport(BaseModel):
    project_name: str = ""
    assessment_date: str = ""
    overall_status: str = ""
    risk_score: float = 0.0
    top_risks: list[str] = Field(default_factory=list)
    key_achievements: list[str] = Field(default_factory=list)
    delayed_milestones: list[str] = Field(default_factory=list)
    critical_tasks: list[str] = Field(default_factory=list)
    upcoming_work: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    executive_summary: str = ""


class TrendPoint(BaseModel):
    date: str = ""
    score: float = 0.0
    rag: str = ""


class ProjectTrend(BaseModel):
    project_name: str = ""
    points: list[TrendPoint] = Field(default_factory=list)
    current_score: float = 0.0
    current_rag: str = ""
    score_delta: float = 0.0
