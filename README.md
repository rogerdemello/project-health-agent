# Project Health Reporting Agent

An AI-powered system that automatically analyzes Microsoft Project exports (Excel) and generates executive project health reports with RAG (Red/Amber/Green) status, plain-English reasoning, and monthly executive presentations.

Built for the Zycus AI Engineer Intern technical assignment.

## Architecture

```
    Excel (.xlsx)
         │
         ▼
  ┌──────────────┐
  │  Parser      │  Fuzzy column detection, handles messy data
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  Pydantic    │  Structured data models (Task, Milestone, etc.)
  │  Models      │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  RAG Engine  │  Deterministic business rules — NO LLM used for scoring
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  LLM Layer   │  LLM explains the pre-computed scores (reasoning only)
  └──────┬───────┘
         │
    ┌────┴────┐
    ▼         ▼
 Weekly    Monthly
 Report    PPTX
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # Add your NVIDIA_API_KEY (free tier at build.nvidia.com)
```

### 1. Analyze a single project

```bash
python main.py analyze data/S2P\ Project.xlsx
python main.py analyze data/Project\ Plan\ B.xlsx
```

### 2. Generate a full weekly report

```bash
python main.py report data/S2P\ Project.xlsx
```

Output: `outputs/Titan_S2P_*.md` and `.json`

### 3. Run monthly synthesis on all projects

```bash
python main.py monthly data/
```

Generates reports for every `.xlsx` in `data/` plus a 6-slide PowerPoint.

### 4. Start the API server

```bash
python main.py serve
```

Then `POST /analyze` with an Excel file to get JSON assessments.

## RAG Methodology

Five weighted dimensions, scored by deterministic business rules (no LLM involvement):

| Dimension | Weight | What It Measures |
|---|---|---|
| Schedule Health | 30% | Task-level health flags + summary sheet fallback |
| Milestones | 25% | Milestone completion % with overdue penalty |
| Critical Tasks | 20% | Overdue critical-path items |
| Variance | 15% | Average schedule variance across tasks |
| Sentiment | 10% | Negative keyword frequency in comments |

**Thresholds:** Green ≥ 85 | Amber 60–84 | Red < 60

### Handling Missing Data

| Scenario | Behavior |
|---|---|
| Missing dates | Task skipped from variance calc |
| Missing completion % | Assumed 0% |
| Missing schedule health | Falls back to Summary sheet or neutral (50) |
| No comments | Sentiment scored as neutral (50) |
| Invalid cells | Logged as warning, skipped gracefully |
| `#UNPARSEABLE` values | Treated as neutral/zero |

## LLM Usage

The LLM (NVIDIA NIM — Llama 3.1, via the OpenAI-compatible endpoint) is used
**only** for executive reasoning:

- **Input**: Structured JSON of pre-computed metrics (never raw Excel)
- **Output**: Plain-English summary, reasons, and recommendations
- **Fallback**: If no API key is configured, a rule-based explanation is used
- **Portable**: OpenAI-compatible, so it also runs against OpenAI directly by
  setting `OPENAI_API_KEY` instead of `NVIDIA_API_KEY`

This ensures deterministic, auditable scoring combined with natural-language communication.

## Project Structure

```
project-health-agent/
├── app/
│   ├── api.py          FastAPI endpoints
│   ├── config.py       Environment & column config
│   ├── llm.py          LLM reasoning (NVIDIA NIM / OpenAI-compatible)
│   ├── models.py       Pydantic v2 data models
│   ├── parser.py       Excel parser with fuzzy column detection
│   ├── ppt.py          PowerPoint generator
│   ├── rag_engine.py   Deterministic scoring engine
│   ├── reports.py      Markdown/JSON report generation
│   └── utils.py        Shared utilities
├── prompts/
│   └── explanation.md  LLM system prompt
├── tests/
│   └── test_all.py     Parser + RAG engine tests
├── data/               Sample Excel project plans
├── outputs/            Generated reports & presentations
├── logs/               Application logs
├── main.py             Typer CLI entry point
├── requirements.txt
└── README.md
```

## Tests

```bash
python -m pytest tests/ -v
```

## Design Decisions

1. **Deterministic RAG Scoring** — Business rules compute the status, not the LLM. The LLM only explains. This ensures consistent, auditable results.
2. **Fuzzy Column Detection** — Columns are matched by name aliases and `difflib` fuzzy matching. No hardcoded indices. Handles variations between different project plan exports.
3. **Pydantic v2 Models** — All data is validated at the boundary. No raw dicts floating around.
4. **Modular Architecture** — Parser → Models → RAG Engine → LLM → Reports → PPTX. Each layer is independently testable and replaceable.
5. **Graceful Degradation** — Missing data never crashes the system. Unknown status defaults to neutral. Fallback explanations work without an API key.

## Future Improvements

- Dashboard with real-time project health visualization
- Automated PDF report generation
- Integration with Jira/MS Project APIs for live data
- Multi-language executive summaries
- Historical trend database for predictive analytics
