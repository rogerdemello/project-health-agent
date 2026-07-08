#!/usr/bin/env python3
"""Project Health Agent - CLI entry point.

Usage:
    python main.py analyze data/project.xlsx
    python main.py report data/project.xlsx --output outputs/
    python main.py monthly data/ --presentation
    python main.py serve
"""

import sys
from pathlib import Path

import typer
from loguru import logger

from app.utils import setup_logging
from app.parser import parse_project
from app.rag_engine import assess
from app.llm import explain
from app.reports import build_report, save_report
from app.ppt import generate_presentation
from app.models import WeeklyReport, RiskAssessment, ProjectTrend

app = typer.Typer()


@app.command()
def analyze(
    filepath: str = typer.Argument(..., help="Path to Excel project plan"),
):
    """Analyze a single project plan and print RAG assessment."""
    setup_logging()
    project = parse_project(filepath)
    assessment = assess(project)
    explanation = explain(assessment)

    typer.echo(f"\n{'='*50}")
    typer.echo(f"  Project: {assessment.project_name}")
    typer.echo(f"  Status:  {assessment.rag} (Score: {assessment.aggregate_score:.0f}/100)")
    typer.echo(f"{'='*50}")
    typer.echo(f"\n  Executive Summary:")
    typer.echo(f"  {explanation.summary}")
    typer.echo(f"\n  Dimension Breakdown:")
    for d in assessment.dimensions:
        typer.echo(f"    - {d.name:20s} {d.score:5.0f}/100 ({d.weight:.0f}%)  {d.detail}")
    if assessment.top_reasons:
        typer.echo(f"\n  Top Issues:")
        for r in assessment.top_reasons:
            typer.echo(f"    * {r}")
    if explanation.recommendations:
        typer.echo(f"\n  Recommendations:")
        for r in explanation.recommendations:
            typer.echo(f"    * {r}")
    typer.echo()


@app.command()
def report(
    filepath: str = typer.Argument(..., help="Path to Excel project plan"),
    output: str = typer.Option("outputs", "--output", "-o", help="Output directory"),
):
    """Generate a full weekly report (Markdown + JSON)."""
    setup_logging()
    project = parse_project(filepath)
    assessment = assess(project)
    explanation = explain(assessment)
    report_obj = build_report(project, assessment, explanation)
    path = save_report(report_obj)
    typer.echo(f"Report saved: {path}")
    typer.echo(report_obj.executive_summary)


@app.command()
def monthly(
    directory: str = typer.Argument("data", help="Directory containing project Excel files"),
    presentation: bool = typer.Option(True, "--presentation", help="Generate PowerPoint"),
):
    """Run assessment on all projects in a directory and generate monthly synthesis."""
    setup_logging()
    data_dir = Path(directory)
    if not data_dir.exists():
        typer.echo(f"Directory not found: {directory}", err=True)
        raise typer.Exit(1)

    xlsx_files = sorted(data_dir.glob("*.xlsx"))
    if not xlsx_files:
        typer.echo(f"No .xlsx files found in {directory}", err=True)
        raise typer.Exit(1)

    reports_list: list[WeeklyReport] = []
    assessments_list: list[RiskAssessment] = []
    trends_list: list[ProjectTrend] = []

    for fp in xlsx_files:
        typer.echo(f"Processing: {fp.name}")
        project = parse_project(str(fp))
        assessment = assess(project)
        explanation = explain(assessment)
        report_obj = build_report(project, assessment, explanation)
        save_path = save_report(report_obj)
        typer.echo(f"  -> {assessment.rag} (Score: {assessment.aggregate_score:.0f}) - {save_path.name}")
        reports_list.append(report_obj)
        assessments_list.append(assessment)
        trends_list.append(ProjectTrend(
            project_name=project.name,
            current_score=assessment.aggregate_score,
            current_rag=assessment.rag,
        ))

    if presentation and reports_list:
        ppt_path = generate_presentation(reports_list, assessments_list, trends_list)
        typer.echo(f"\nPresentation: {ppt_path}")

    typer.echo(f"\nDone. {len(reports_list)} projects analyzed.")


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
):
    """Start the FastAPI web service."""
    setup_logging()
    typer.echo(f"Starting API at http://{host}:{port}")
    typer.echo(f"Docs at http://{host}:{port}/docs")
    import uvicorn
    uvicorn.run("app.api:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    app()
