from state import IncidentState
from tools.common_functions import get_llm, parse_json
from tools.github_client import create_pull_request

llm = get_llm()

SQL_FIX_PROMPT = """
You are an expert dbt engineer.

Failure:
\"\"\"
{error}
\"\"\"

Original SQL:
\"\"\"
{sql}
\"\"\"

Fix the SQL.

Return ONLY JSON:

{{
  "fixed_sql": "<correct SQL>",
  "summary": "<what was changed>",
  "risk_level": "<low | medium | high>"
}}
"""


def raise_pr(state: IncidentState) -> IncidentState:
    print("\nLLM PR AGENT RUNNING")

    raw_sql = state.get("raw_sql")
    file_path = state.get("file_path")
    error = state.get("description")

    prompt = SQL_FIX_PROMPT.format(
        error=error,
        sql=raw_sql
    )

    response = llm.invoke(prompt)
    parsed = parse_json(response.content if hasattr(response, "content") else str(response))

    if not parsed:
        state["recommended_action"] = "escalate"
        return state

    if parsed.get("risk_level") == "high":
        state["recommended_action"] = "escalate"
        return state

    pr_url = create_pull_request(
        file_path=file_path,
        updated_content=parsed["fixed_sql"],
        title="AI Auto-Fix: dbt Failure",
        body=f"""
Root Cause: {state.get("rca_reason")}

Summary:
{parsed.get("summary")}
"""
    )

    state["pr_url"] = pr_url
    print(f"PR Created: {pr_url}")

    return state
