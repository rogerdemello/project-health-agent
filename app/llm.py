"""LLM-based executive reasoning.

The LLM NEVER calculates RAG. It only explains the already-computed metrics.
"""

from openai import OpenAI
from loguru import logger

from app.models import RiskAssessment, LLMExplanation
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


_EXPLANATION_PROMPT = """You are a PMO Executive presenting to client leadership.

Given the following project metrics, explain the health status in plain English.

Project: {project_name}
RAG Status: {rag}
Aggregate Score: {score}/100

Dimension Scores:
{dimensions}

Top Issues:
{issues}

{missing_data_note}

Instructions:
- Explain why the project is {rag} in clear, executive-friendly language.
- Do NOT invent metrics or recalculate anything.
- Do NOT mention scores or numbers unless essential.
- Write 2-3 paragraphs max.
- Suggest 3 actionable recommendations.

Output format:
Summary: <one paragraph>
Reasons: <bullet points>
Recommendations: <bullet points>"""


def _build_prompt(assessment: RiskAssessment) -> str:
    dims_str = "\n".join(
        f"  - {d.name}: {d.score:.0f}/100 ({d.weight:.0f}% weight) - {d.detail}"
        for d in assessment.dimensions
    )
    issues = "\n".join(f"  - {r}" for r in assessment.top_reasons[:5])
    missing = ""
    if assessment.missing_data_flags:
        missing = f"Note: The following data was missing: {', '.join(assessment.missing_data_flags)}. Assessment used defaults."
    return _EXPLANATION_PROMPT.format(
        project_name=assessment.project_name,
        rag=assessment.rag,
        score=assessment.aggregate_score,
        dimensions=dims_str,
        issues=issues if issues else "  - None",
        missing_data_note=missing,
    )


def explain(assessment: RiskAssessment, client: OpenAI | None = None) -> LLMExplanation:
    """Use LLM to generate executive explanation for a computed assessment."""
    if not LLM_API_KEY:
        logger.warning("No LLM API key set (NVIDIA_API_KEY/OPENAI_API_KEY); returning rule-based explanation.")
        return _fallback_explanation(assessment)

    if client is None:
        # NVIDIA NIM is OpenAI-compatible: same SDK, different base_url.
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL or None, timeout=120)
    prompt = _build_prompt(assessment)

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a PMO Executive. Be concise, professional, and insightful."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        text = response.choices[0].message.content or ""
        logger.info(f"LLM explanation generated ({len(text)} chars)")
        return _parse_llm_response(text, assessment)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return _fallback_explanation(assessment)


def _parse_llm_response(text: str, assessment: RiskAssessment) -> LLMExplanation:
    """Parse the structured LLM response."""
    explanation = LLMExplanation()
    lines = text.strip().split("\n")
    current_section = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("Summary:") or line.startswith("Summary"):
            current_section = "summary"
            explanation.summary = line.split(":", 1)[1].strip() if ":" in line else ""
        elif line.startswith("Reasons:") or line.startswith("Reasons"):
            current_section = "reasons"
        elif line.startswith("Recommendations:") or line.startswith("Recommendations"):
            current_section = "recommendations"
        elif current_section == "summary":
            explanation.summary += " " + line
        elif current_section == "reasons":
            clean = line.lstrip("- *").strip()
            if clean:
                explanation.reasons.append(clean)
        elif current_section == "recommendations":
            clean = line.lstrip("- *").strip()
            if clean:
                explanation.recommendations.append(clean)

    if not explanation.summary:
        explanation.summary = text[:300]
    if not explanation.reasons:
        explanation.reasons = assessment.top_reasons[:3]
    return explanation


def _fallback_explanation(assessment: RiskAssessment) -> LLMExplanation:
    """Generate a rule-based explanation when LLM is unavailable."""
    reasons = []
    for d in sorted(assessment.dimensions, key=lambda x: x.score):
        if d.score < 60:
            reasons.append(f"{d.name}: {d.detail[:100]}")
    if not reasons:
        reasons.append("All dimensions are within acceptable range.")

    recs = []
    for r in reasons[:3]:
        recs.append(f"Address {r.split(':')[0].lower()} gaps.")

    summary = (
        f"The project is currently {assessment.rag} with a score of {assessment.aggregate_score:.0f}/100. "
        f"{' & '.join(r.split(':')[0] for r in reasons[:2])} are the primary concerns."
    ) if reasons else f"The project is {assessment.rag} with no significant issues detected."

    return LLMExplanation(
        summary=summary,
        reasons=reasons[:3],
        recommendations=recs if recs else ["Continue monitoring all dimensions."],
    )
