import json
from typing import Optional
from state import IncidentState
from tools.llm_client import get_llm

llm = get_llm()

# -----------------------------
# Configuration
# -----------------------------

ALLOWED_INCIDENT_TYPES = {
    "data_quality",
    "pipeline_failure",
    "config_issue",
    "performance_issue",
    "dependency_issue",
    "unknown"
}

CLASSIFICATION_PROMPT = """
You are an AI Ops incident classification agent.

Classify the following incident related to dbt, Databricks, or data pipelines.

Incident description:
\"\"\"
{description}
\"\"\"

Allowed incident types:
- data_quality
- pipeline_failure
- config_issue
- performance_issue
- dependency_issue
- unknown

IMPORTANT:
- Do NOT use markdown
- Do NOT include explanations outside JSON
- Do NOT wrap the response in ```json or ``` blocks
- Output MUST be valid, parseable JSON
- If unsure, return "incident_type": "unknown"

Any response that is not valid JSON will be considered a failure.

Return ONLY valid JSON in the following format:

{{
  "incident_type": "<one of the allowed values>",
  "confidence": "<low | medium | high>",
  "reason": "<short explanation>"
}}
"""


# -----------------------------
# Utility functions
# -----------------------------

def safe_json_loads(text: Optional[str]):
    """
    Safely parse JSON.
    Returns None if parsing fails.
    """
    if text is None:
        return None

    if not isinstance(text, str):
        return None

    text = text.strip()

    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def normalize_incident_type(value: Optional[str]) -> str:
    """
    Ensures incident_type is valid.
    """
    if not value or not isinstance(value, str):
        return "unknown"

    value = value.strip().lower()

    if value in ALLOWED_INCIDENT_TYPES:
        return value

    return "unknown"


# -----------------------------
# LangGraph Node
# -----------------------------

def classify_incident(state: IncidentState) -> IncidentState:
    """
    LangGraph node:
    - Builds classification prompt
    - Calls LLM
    - Safely parses and validates output
    """

    description = state.get("description", "")

    # ---- Build prompt safely ----
    prompt = CLASSIFICATION_PROMPT.format(
        description=description
    )

    response = llm.invoke(prompt)
    # print("Prompt sent to LLM:")
    # print(prompt)
 
    print("Raw LLM response:")
    print(response)
    if hasattr(response, "content"):
        response_text = response.content
    else:
        response_text = str(response)

    print("LLM response text:")
    print(response_text)

    parsed = safe_json_loads(response_text)

    print("Parsed JSON:")
    print(parsed)

    incident_type = normalize_incident_type(
        parsed.get("incident_type") if parsed else None
    )

    confidence = parsed.get("confidence", "low") if parsed else "low"
    reason = parsed.get(
        "reason",
        "LLM response missing or invalid"
    ) if parsed else "LLM response missing or invalid"

    # ---- Update state ----
    state["incident_type"] = incident_type
    state["explanation"] = reason
    state["confidence"] = confidence

    # print(f"Incident classified as: {incident_type} (confidence={confidence})")

    return state
