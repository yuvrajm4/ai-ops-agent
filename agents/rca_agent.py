import json
import re
from typing import List
from state import IncidentState
from tools.common_functions import get_llm, parse_json
from memory.vector_store import IncidentVectorStore

# ---------------------------------------------------
# Initialization
# ---------------------------------------------------

store = IncidentVectorStore()
llm = get_llm()

MANIFEST_PATH = "target/manifest.json"

RCA_PROMPT = """
You are an expert dbt root cause analysis agent.

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
  "recommended_action": "<retry_run | fix_dependency_break | create_pr | escalate>",
  "reason": "<short explanation>"
}}
"""


# ---------------------------------------------------
# Helper Functions
# ---------------------------------------------------

def load_manifest():
    try:
        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None


def extract_missing_column(description: str):
    match = re.search(r"Column\s+([a-zA-Z0-9_]+)\s+does not exist", description)
    return match.group(1) if match else None


def extract_type_mismatch(description: str):
    match = re.search(
        r"Column\s+(\w+)\s+has type\s+(\w+)\s+but expected\s+(\w+)",
        description
    )
    if match:
        return {
            "column": match.group(1),
            "actual_type": match.group(2),
            "expected_type": match.group(3)
        }
    return None


# ---------------------------------------------------
# LangGraph Node
# ---------------------------------------------------

def analyze_root_cause(state: IncidentState) -> IncidentState:
    print("\nRCA + IMPACT AGENT RUNNING")

    # ---------------------------------------------------
    # Preserve Operational Metadata (CRITICAL)
    # ---------------------------------------------------

    job_id = state.get("job_id")
    dbt_run_id = state.get("dbt_run_id")
    incident_id = state.get("incident_id") or str(dbt_run_id)

    if not job_id:
        print("⚠️ WARNING: No job_id found in state. Retry will not work.")

    # Explicitly preserve
    state["job_id"] = job_id
    state["dbt_run_id"] = dbt_run_id
    state["incident_id"] = incident_id

    # ---------------------------------------------------
    # Core RCA Logic
    # ---------------------------------------------------

    description = state.get("description", "")
    incident_type = state.get("incident_type", "unknown")
    model_name = state.get("model_name")

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

    response = llm.invoke(prompt)
    response_text = response.content if hasattr(response, "content") else str(response)

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

    # ---------------------------------------------------
    # Manifest Impact Analysis
    # ---------------------------------------------------

    manifest = load_manifest()

    if manifest and model_name and model_name in manifest.get("nodes", {}):

        node = manifest["nodes"][model_name]

        upstream = node.get("depends_on", {}).get("nodes", [])

        downstream = [
            key for key, value in manifest["nodes"].items()
            if model_name in value.get("depends_on", {}).get("nodes", [])
        ]

        state["upstream_models"] = upstream
        state["downstream_models"] = downstream

        # ---------------- Missing Column ----------------

        missing_column = extract_missing_column(description)

        if missing_column:
            print(f"Detected missing column: {missing_column}")
            state["missing_column"] = missing_column

            impacted_models = []

            for child in downstream:
                child_sql = manifest["nodes"][child].get("raw_sql", "")
                if missing_column in child_sql:
                    impacted_models.append(child)

            state["impacted_models"] = impacted_models
            state["blast_radius"] = len(impacted_models)

            if impacted_models:
                state["recommended_action"] = "fix_dependency_break"

        # ---------------- Type Mismatch ----------------

        type_mismatch = extract_type_mismatch(description)

        if type_mismatch:
            print("Detected data type mismatch.")
            state["type_mismatch"] = type_mismatch

            column = type_mismatch["column"]

            impacted_models = []

            for child in downstream:
                child_sql = manifest["nodes"][child].get("raw_sql", "")
                if column in child_sql:
                    impacted_models.append(child)

            state["impacted_models"] = impacted_models
            state["blast_radius"] = len(impacted_models)

            if impacted_models:
                state["recommended_action"] = "fix_dependency_break"

    # ---------------------------------------------------
    # Retry Safety Guard
    # ---------------------------------------------------

    if state.get("recommended_action") == "retry_run":
        if not state.get("job_id"):
            print("❌ Retry requested but job_id missing. Escalating instead.")
            state["recommended_action"] = "escalate"

    # ---------------------------------------------------
    # Memory Learning
    # ---------------------------------------------------

    primary_root_cause = root_causes[0]["cause"] if root_causes else "Unknown"

    print(f"\nPrimary Root cause: {primary_root_cause}")
    print(f"Recommended action: {state['recommended_action']}")
    print(f"Job ID available for retry: {state.get('job_id')}")
    print(f"Blast radius: {state.get('blast_radius', 0)}")

    store.add_incident(
        incident_id=incident_id,
        description=description,
        incident_type=incident_type,
        root_cause=primary_root_cause
    )

    print("Root cause stored in Vector DB")

    return state
