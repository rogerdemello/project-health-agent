"""Tests for Project Health Agent.

Run with: python -m pytest tests/ -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Task, Milestone, ParsedProject, RiskAssessment, DimensionScore
from app.rag_engine import (
    _score_schedule_health,
    _score_milestones,
    _score_critical_tasks,
    _score_variance,
    _score_sentiment,
    assess,
)
from app.parser import parse_project, parse_date, parse_variance, parse_percent


class TestParsing:
    def test_parse_date(self):
        from datetime import date
        assert parse_date(None) is None
        assert parse_date("2026-07-08") == date(2026, 7, 8)

    def test_parse_variance(self):
        assert parse_variance(None) is None
        assert parse_variance("-6d") == -6.0
        assert parse_variance("0") == 0.0
        assert parse_variance("#UNPARSEABLE") == 0.0
        assert parse_variance(5) == 5.0

    def test_parse_percent(self):
        assert parse_percent(None) == 0.0
        assert parse_percent(0.75) == 75.0
        assert parse_percent(75) == 75.0
        assert parse_percent("50%") == 50.0
        assert parse_percent(0) == 0.0

    def test_parse_project_s2p(self):
        project = parse_project("data/S2P Project.xlsx")
        assert "Titan" in project.name or "S2P" in project.name
        assert project.tasks
        assert project.comments is not None

    def test_parse_project_plan_b(self):
        project = parse_project("data/Project Plan B.xlsx")
        assert "UniSan" in project.name or "S2P" in project.name
        assert project.tasks
        assert project.comments is not None


class TestRagEngine:
    def test_schedule_health_green(self):
        project = ParsedProject()
        project.tasks = [
            Task(name="T1", schedule_health="Green", status="Completed", percent_complete=100),
            Task(name="T2", schedule_health="Green", status="In Progress", percent_complete=50),
        ]
        score = _score_schedule_health(project)
        assert score.score == 100.0

    def test_schedule_health_mixed(self):
        project = ParsedProject()
        project.tasks = [
            Task(name="T1", schedule_health="Green"),
            Task(name="T2", schedule_health="Amber"),
            Task(name="T3", schedule_health="Red"),
        ]
        score = _score_schedule_health(project)
        assert 0 < score.score < 100

    def test_schedule_health_empty_fallback(self):
        project = ParsedProject()
        project.raw_summary = {"Schedule Health": "Red"}
        score = _score_schedule_health(project)
        assert score.score == 25

    def test_milestones_all_complete(self):
        project = ParsedProject()
        project.milestones = [
            Milestone(name="M1", completed=True, percent_complete=100),
            Milestone(name="M2", completed=True, percent_complete=100),
        ]
        score = _score_milestones(project)
        assert score.score >= 90

    def test_milestones_overdue(self):
        project = ParsedProject()
        project.milestones = [
            Milestone(name="M1", completed=False, percent_complete=50, variance_days=-10),
            Milestone(name="M2", completed=False, percent_complete=30, variance_days=-5),
        ]
        score = _score_milestones(project)
        assert score.score < 60

    def test_critical_tasks_all_good(self):
        project = ParsedProject()
        project.tasks = [
            Task(name="C1", critical=True, status="Completed", percent_complete=100),
            Task(name="C2", critical=True, status="Completed", percent_complete=100),
        ]
        score = _score_critical_tasks(project)
        assert score.score >= 80

    def test_critical_tasks_overdue(self):
        project = ParsedProject()
        project.tasks = [
            Task(name="C1", critical=True, status="In Progress", variance_days=-10),
            Task(name="C2", critical=True, status="In Progress", variance_days=-20),
        ]
        score = _score_critical_tasks(project)
        assert score.score <= 70

    def test_variance_on_track(self):
        project = ParsedProject()
        project.tasks = [
            Task(name="T1", variance_days=0),
            Task(name="T2", variance_days=1),
            Task(name="T3", variance_days=-1),
        ]
        score = _score_variance(project)
        assert score.score >= 80

    def test_variance_severe(self):
        project = ParsedProject()
        project.tasks = [Task(name=f"T{i}", variance_days=-25) for i in range(10)]
        score = _score_variance(project)
        assert score.score <= 30

    def test_sentiment_positive(self):
        project = ParsedProject()
        project.tasks = [Task(name="T1", comments="Great progress, team is ahead")]
        score = _score_sentiment(project)
        assert score.score >= 80

    def test_sentiment_negative(self):
        project = ParsedProject()
        project.tasks = [Task(name="T1", comments="blocked by dependency"),
                         Task(name="T2", comments="delay in delivery, concerns about timeline")]
        score = _score_sentiment(project)
        assert score.score <= 70

    def test_sentiment_empty(self):
        project = ParsedProject()
        score = _score_sentiment(project)
        assert score.missing_data
        assert score.score == 50

    def test_full_assessment(self):
        project = ParsedProject(name="Test Project")
        project.tasks = [
            Task(name="T1", schedule_health="Green", status="Completed", percent_complete=100),
            Task(name="T2", schedule_health="Green", status="In Progress", percent_complete=60),
            Task(name="T3", critical=True, status="In Progress", variance_days=0),
        ]
        project.milestones = [
            Milestone(name="M1", completed=True, percent_complete=100),
            Milestone(name="M2", completed=False, percent_complete=60, variance_days=0),
        ]
        assessment = assess(project)
        assert assessment.rag in ("Green", "Amber", "Red")
        assert assessment.aggregate_score > 0
        assert assessment.project_name == "Test Project"
        assert len(assessment.dimensions) == 5
