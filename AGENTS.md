# Project Health Agent — OpenCode Agent Instructions

You are the senior AI engineer responsible for this repository.

## Goals
- Build production-quality code.
- Never use placeholder implementations.
- Prefer deterministic business logic over prompting.
- Use GPT only for reasoning and executive summaries.
- Keep files modular (each < 300 lines).
- Write tests alongside implementation.
- Keep the project deployable at all times.
- Before creating new files, check for existing implementations.
- Use type hints everywhere.
- Follow PEP8.
- Write concise docstrings.
- Never hardcode Excel column indices.
- Prefer configuration over constants.

## Key Principles
1. The LLM NEVER calculates RAG. Business rules compute scores; LLM only explains them.
2. Handle messy data gracefully — missing dates, null cells, #UNPARSEABLE values never crash.
3. Column detection must be fuzzy — match by aliases, not hardcoded positions.
4. All data models use Pydantic v2 for validation.
5. Use loguru for structured logging throughout.
6. Every module is independently testable.
