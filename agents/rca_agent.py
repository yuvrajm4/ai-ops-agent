from typing import List
from state import IncidentState
from tools.common_functions import get_llm, parse_json

llm = get_llm()

RCA_PROMPT = """
You are an AI Ops Root Cause Analysis agent.

Incident description:
\"\"\"
{description}
\"\"\"

Incident type: {incident_type}

Given this incident, identify the most likely root causes.

IMPORTANT:
- Do NOT use markdown
- Do NOT include explanations outside JSON
- Do NOT wrap the response in ```json or ``` blocks
- Output MUST be valid, parseable JSON

Required format:
{{
  "root_causes": [
    {{
      "cause": "<short description>",
      "confidence": "<low | medium | high>"
    }}
  ],
  "recommended_action": "<auto_fix | create_pr | escalate>",
  "reason": "<short explanation>"
}}
"""

# -----------------------------
# LangGraph Node
# -----------------------------

def analyze_root_cause(state: IncidentState) -> IncidentState:
    description = state.get("description", "")
    incident_type = state.get("incident_type", "unknown")

    prompt = RCA_PROMPT.format(
        description=description,
        incident_type=incident_type
    )

    # print("\n RCA Prompt:")
    # print(prompt)

    response = llm.invoke(prompt)

    if hasattr(response, "content"):
        response_text = response.content
    else:
        response_text = str(response)

    # print("\n RCA Response:")
    # print(response_text)

    parsed = parse_json(response_text)

    if not parsed:
        state["root_causes"] = []
        state["recommended_action"] = "escalate"
        state["rca_reason"] = "Unable to determine root cause"
        return state

    state["root_causes"] = parsed.get("root_causes", [])
    state["recommended_action"] = parsed.get("recommended_action", "escalate")
    state["rca_reason"] = parsed.get("reason", "")

    print(f"\n Recommended action: {state['recommended_action']}")

    return state
