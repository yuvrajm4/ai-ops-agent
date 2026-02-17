from langgraph.graph import StateGraph
from state import IncidentState
from agents.incident_agent import classify_incident
from agents.rca_agent import analyze_root_cause
from agents.retry_agent import retry_agent_node
from agents.escalation_agent import escalation_node


# ---------------------------------
# Routing After RCA
# ---------------------------------

def route_after_rca(state: IncidentState) -> str:
    """
    Route based on RCA decision.
    """

    # If RCA confidence is low → escalate
    if state.get("confidence") == "low":
        return "escalate"

    action = state.get("recommended_action")

    if action == "retry_run":
        return "retry"

    return "escalate"



# ---------------------------------
# Build Graph
# ---------------------------------

def build_graph():
    graph = StateGraph(IncidentState)

    graph.add_node("classify", classify_incident)
    graph.add_node("rca", analyze_root_cause)
    graph.add_node("retry", retry_agent_node)
    graph.add_node("escalate", escalation_node)

    graph.set_entry_point("classify")

    graph.add_edge("classify", "rca")

    graph.add_conditional_edges(
        "rca",
        route_after_rca,
        {
            "retry": "retry",
            "escalate": "escalate",
        }
    )

    # Important:
    # retry_agent_node already escalates internally if needed
    # So no outgoing edge required from retry

    return graph.compile()


# ---------------------------------
# Run Workflow
# ---------------------------------

def run_workflow(state: IncidentState):
    app = build_graph()
    return app.invoke(state)
