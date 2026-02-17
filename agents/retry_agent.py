import json
from typing import Optional
from state import IncidentState
from tools.common_functions import (
    get_llm,
    parse_json,
    retry_dbt_cloud_job
)
from agents.escalation_agent import escalation_node


# -----------------------------
# LLM Setup
# -----------------------------

llm = get_llm()


# -----------------------------
# Retry Decision Prompt
# -----------------------------

RETRY_EXECUTION_PROMPT = """
You are an AI Ops Autonomous Retry Agent for dbt Cloud.

A dbt Cloud job has failed.

Incident Details:
Description: {description}
Type: {incident_type}
Confidence: {confidence}

Job ID: {job_id}

Your task:
1. Decide whether the job should be retried.
2. If yes, determine:
   - max_attempts (1-3)
   - delay_seconds (5-60)

Rules:
- Retry only transient failures (timeouts, infra, temporary errors).
- Do NOT retry configuration issues, schema mismatches, missing columns, syntax errors.
- If confidence is low, prefer escalation.
- Output ONLY valid JSON.
- No markdown.
- No explanations outside JSON.

Return:

{{
  "retry": true/false,
  "max_attempts": <number>,
  "delay_seconds": <number>,
  "reason": "<short explanation>"
}}
"""


# -----------------------------
# Retry Agent Node
# -----------------------------

def retry_agent_node(state: IncidentState) -> IncidentState:
    """
    LangGraph Node:
    - LLM decides retry strategy
    - Executes dbt Cloud retry
    - Updates state
    - Escalates automatically if needed
    """

    print("\n🔁 RETRY AGENT STARTED")

    description = state.get("description", "")
    incident_type = state.get("incident_type", "unknown")
    confidence = state.get("confidence", "low")
    job_id = state.get("job_id")

    if not job_id:
        print("❌ No job_id found in state. Escalating.")
        state["retry_status"] = "missing_job_id"
        return escalation_node(state)

    # -----------------------------
    # LLM Reasoning
    # -----------------------------

    prompt = RETRY_EXECUTION_PROMPT.format(
        description=description,
        incident_type=incident_type,
        confidence=confidence,
        job_id=job_id
    )

    response = llm.invoke(prompt)

    response_text = response.content if hasattr(response, "content") else str(response)

    print(response_text)

    parsed = parse_json(response_text)

    if not parsed:
        print("⚠️ LLM returned invalid JSON. Escalating.")
        state["retry_status"] = "llm_parse_failed"
        return escalation_node(state)

    should_retry = parsed.get("retry", False)
    reason = parsed.get("reason", "No reason provided")

    print(f"LLM Decision: retry={should_retry} | reason={reason}")

    if not should_retry:
        print("🚨 Retry not recommended. Escalating.")
        state["retry_status"] = "not_recommended"
        state["retry_reason"] = reason
        return escalation_node(state)

    # -----------------------------
    # Safe Limits
    # -----------------------------

    max_attempts = min(max(int(parsed.get("max_attempts", 1)), 1), 3)
    delay_seconds = min(max(int(parsed.get("delay_seconds", 10)), 5), 60)

    print(f"Executing retry: attempts={max_attempts}, delay={delay_seconds}s")

    # -----------------------------
    # Execute Retry
    # -----------------------------

    result = retry_dbt_cloud_job(
        job_id=job_id,
        max_attempts=max_attempts,
        delay_seconds=delay_seconds
    )

    # -----------------------------
    # Handle Result
    # -----------------------------

    if result.get("success"):
        print("✅ Retry succeeded")

        state["retry_status"] = "success"
        state["retry_attempts"] = result.get("attempts")
        state["dbt_run_id"] = result.get("run_id")
        state["retry_reason"] = reason

        return state

    print("❌ Retry failed. Escalating.")

    state["retry_status"] = "failed"
    state["retry_attempts"] = result.get("attempts")
    state["retry_reason"] = result.get("reason", "unknown_failure")

    return escalation_node(state)
