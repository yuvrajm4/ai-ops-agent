import json
import requests
from state import IncidentState
from tools.common_functions import get_llm, parse_json

# -----------------------------
# LLM Setup
# -----------------------------

llm = get_llm()


# -----------------------------
# Escalation Prompt
# -----------------------------

ESCALATION_PROMPT = """
You are an AI Ops Escalation Agent.

A dbt Cloud pipeline failure requires human intervention.

Incident Details:
Description: {description}
Incident Type: {incident_type}
Confidence: {confidence}
Retry Status: {retry_status}
Root Cause: {root_cause}
Run ID: {run_id}

Your task:
Generate a professional Slack alert message.

Rules:
- Be concise but informative.
- Include impact summary.
- Include recommended next steps.
- Assign priority: P1 (critical), P2 (major), P3 (minor)
- Output ONLY valid JSON.
- No markdown.
- No explanations outside JSON.

Return:

{{
  "title": "<short alert title>",
  "priority": "<P1|P2|P3>",
  "summary": "<1-2 sentence summary>",
  "impact": "<business or data impact>",
  "recommended_action": "<clear next step for engineer>"
}}
"""


# -----------------------------
# Escalation Node
# -----------------------------

def escalation_node(state: IncidentState) -> IncidentState:
    """
    LangGraph Node:
    - LLM drafts escalation message
    - Prints formatted Slack payload
    - Slack POST is commented (enable later)
    """

    print("\n🚨 ESCALATION AGENT TRIGGERED")

    prompt = ESCALATION_PROMPT.format(
        description=state.get("description", "N/A"),
        incident_type=state.get("incident_type", "unknown"),
        confidence=state.get("confidence", "low"),
        retry_status=state.get("retry_status", "not_attempted"),
        root_cause=state.get("root_cause", "Not determined"),
        run_id=state.get("dbt_run_id", "N/A")
    )

    response = llm.invoke(prompt)
    response_text = response.content if hasattr(response, "content") else str(response)

    parsed = parse_json(response_text)

    # Fallback if LLM JSON fails
    if not parsed:
        parsed = {
            "title": "dbt Pipeline Failure",
            "priority": "P2",
            "summary": "A dbt Cloud job failed and requires attention.",
            "impact": "Potential downstream data impact.",
            "recommended_action": "Review logs and fix failing model."
        }

    # -----------------------------
    # Format Slack-style Message
    # -----------------------------

    slack_message = f"""
========================================
🚨 INCIDENT ESCALATION ALERT
========================================
Title: {parsed.get("title")}
Priority: {parsed.get("priority")}

Summary:
{parsed.get("summary")}

Impact:
{parsed.get("impact")}

Recommended Action:
{parsed.get("recommended_action")}

Run ID: {state.get("dbt_run_id", "N/A")}
========================================
"""

    print(slack_message)

    # -----------------------------
    # Slack Webhook (DISABLED)
    # -----------------------------
    #
    # To enable Slack:
    #
    # 1. export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"
    # 2. Uncomment the block below
    #
    # import os
    #
    # SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")
    #
    # if SLACK_WEBHOOK:
    #     response = requests.post(
    #         SLACK_WEBHOOK,
    #         json={"text": slack_message},
    #         headers={"Content-Type": "application/json"}
    #     )
    #
    #     if response.status_code != 200:
    #         print("❌ Slack notification failed:", response.text)
    #     else:
    #         print("✅ Slack notification sent successfully")
    #

    # -----------------------------
    # Update State
    # -----------------------------

    state["escalated"] = True
    state["escalation_payload"] = parsed

    return state
