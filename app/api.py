"""FastAPI service for project health reporting."""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import shutil
import tempfile

from loguru import logger

from app.models import RiskAssessment, LLMExplanation
from app.parser import parse_project
from app.rag_engine import assess
from app.llm import explain
from app.reports import build_report, to_markdown, save_report
from app.config import OUTPUT_DIR

app = FastAPI(title="Project Health Agent", version="1.0.0")


@app.get("/")
def root():
    return {"service": "Project Health Agent", "version": "1.0.0"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """Upload an Excel project plan and get a full health assessment."""
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only .xlsx files accepted.")

    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        project = parse_project(tmp_path)
        assessment = assess(project)
        explanation = explain(assessment)
        report = build_report(project, assessment, explanation)
        return {
            "project": report.project_name,
            "status": report.overall_status,
            "score": report.risk_score,
            "summary": report.executive_summary,
            "reasons": report.top_risks,
            "recommendations": report.recommendations,
            "dimensions": [d.model_dump() for d in assessment.dimensions],
        }
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(500, str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/report")
async def generate_report(file: UploadFile = File(...)):
    """Upload a project plan and get a full Markdown weekly report."""
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only .xlsx files accepted.")

    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        project = parse_project(tmp_path)
        assessment = assess(project)
        explanation = explain(assessment)
        report = build_report(project, assessment, explanation)
        md = to_markdown(report)
        return {"markdown": md, "report": report.model_dump()}
    except Exception as e:
        logger.exception("Report generation failed")
        raise HTTPException(500, str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/outputs/{filename}")
def get_output(filename: str):
    """Retrieve a generated report file."""
    fpath = OUTPUT_DIR / filename
    if not fpath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(fpath)
