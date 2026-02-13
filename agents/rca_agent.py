from typing import List
from state import IncidentState
from tools.common_functions import get_llm, parse_json, get_embeddings
from memory.vector_store import IncidentVectorStore

store = IncidentVectorStore()

llm = get_llm()

RCA_PROMPT = """
You are an AI Ops Root Cause Analysis agent.

Incident description:
\"\"\"
{description}
\"\"\"

Incident type: {incident_type}

Similar historical incidents:
{similar_incidents}

Given this incident AND historical patterns, identify the most likely root causes.

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
    print("\nPERFORMING RCA")
    description = state.get("description", "")
    incident_type = state.get("incident_type", "unknown")
    incident_id = state.get("incident_id", "")

    similar_incidents = store.search_similar(description)

    memory_context = "\n\n".join(
        f"- {item['content']}"
        for item in similar_incidents
    )

    prompt = RCA_PROMPT.format(
    description=description,
    incident_type=incident_type,
    similar_incidents=memory_context or "No similar incidents found"
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

    root_causes = parsed.get("root_causes", [])
    recommended_action = parsed.get("recommended_action", "escalate")

    state["root_causes"] = root_causes
    state["recommended_action"] = recommended_action
    state["rca_reason"] = parsed.get("reason", "")

    #  MEMORY WRITE — THIS IS AUTO-LEARNING
    primary_root_cause = root_causes[0]["cause"] if root_causes else "Unknown"
    
    print(f"\nPrimary Root cause: {primary_root_cause}")
    print(f"\nRecommended action: {state['recommended_action']}")

    store.add_incident(
        incident_id=incident_id,
        description=description,
        incident_type=incident_type,
        root_cause=primary_root_cause
    )

    print(f"Learned from incident: {incident_type}")
    print(f"Root cause stored in Vector DB")

    return state
