import json
from typing import Optional
from state import IncidentState
from tools.common_functions import get_llm, parse_json, get_embeddings
from memory.vector_store import IncidentVectorStore

store = IncidentVectorStore()

llm = get_llm()

# -----------------------------
# Configuration
# -----------------------------

ALLOWED_INCIDENT_TYPES = {
    "transient_infra",
    "performance_issue",
    "dependency_issue",
    "data_type_mismatch",
    "logical_error",
    "data_quality",
    "config_issue",
    "permission_issue",
    "pipeline_failure",
    "unknown"
}

CLASSIFICATION_PROMPT = """
You are an AI Ops incident classification agent.

Classify the following dbt/Databricks/data pipeline incident.

Incident description:
\"\"\"
{description}
\"\"\"

Similar historical incidents:
{similar_incidents}

Allowed incident types:
- transient_infra (timeouts, infra instability)
- performance_issue (memory exceeded, resource limits)
- dependency_issue (missing column, upstream model change)
- data_type_mismatch (type incompatibility)
- logical_error (incorrect join/filter logic)
- data_quality (test failures: unique/not_null/etc)
- config_issue (misconfiguration)
- permission_issue (access denied)
- pipeline_failure (orchestration failure)
- unknown

Return ONLY valid JSON:

{{
  "incident_type": "<one of the allowed values>",
  "confidence": "<low | medium | high>",
  "reason": "<short explanation>"
}}
"""

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

def rule_based_classification(description: str) -> Optional[str]:
    desc = description.lower()

    # Retryable infra issues
    if "memory" in desc or "exceeded" in desc:
        return "performance_issue"

    if "timeout" in desc or "network" in desc:
        return "transient_infra"

    # Code / PR issues
    if "does not exist" in desc or "column" in desc:
        return "dependency_issue"

    if "invalid argument types" in desc or "cannot apply operator" in desc:
        return "data_type_mismatch"

    if "unique test failed" in desc or "not null test failed" in desc:
        return "data_quality"

    if "permission denied" in desc or "access denied" in desc:
        return "permission_issue"

    return None

# -----------------------------
# LangGraph Node
# -----------------------------

def classify_incident(state: IncidentState) -> IncidentState:
    print("\nCLASSIFYING INCIDENT")

    description = state.get("description", "")
    rule_type = rule_based_classification(description)

    # If deterministic rule found → skip LLM
    if rule_type:
        incident_type = rule_type
        confidence = "high"
        reason = "Rule-based classification matched known error pattern"

    else:
        similar_incidents = store.search_similar(description, k=3)

        memory_context = "\n\n".join(
            f"- {getattr(item, 'page_content', str(item))}"
            for item in similar_incidents
        )

        prompt = CLASSIFICATION_PROMPT.format(
            description=description,
            similar_incidents=memory_context or "No similar incidents found"
        )

        response = llm.invoke(prompt)

        response_text = response.content if hasattr(response, "content") else str(response)

        parsed = parse_json(response_text)

        incident_type = normalize_incident_type(
            parsed.get("incident_type") if parsed else None
        )

        confidence = parsed.get("confidence", "low") if parsed else "low"
        reason = parsed.get(
            "reason",
            "LLM response missing or invalid"
        ) if parsed else "LLM response missing or invalid"

    state["incident_type"] = incident_type
    state["explanation"] = reason
    state["confidence"] = confidence

    print(f"Incident classified as: {incident_type} (confidence={confidence})")

    return state
