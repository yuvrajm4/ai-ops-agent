from langgraph.graph import StateGraph
from state import IncidentState
from agents.incident_agent import classify_incident
from agents.rca_agent import analyze_root_cause

def decide_next_step(state: IncidentState) -> str:
    confidence = state.get("confidence", "low")

    if confidence in ["high", "medium"]:
        return "rca"

    return "end"

def build_graph():
    graph = StateGraph(IncidentState)

    graph.add_node("classify", classify_incident)
    graph.add_node("rca", analyze_root_cause)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        decide_next_step,
        {
            "rca": "rca",
            "end": "__end__"
        }
    )

    graph.set_finish_point("rca")

    return graph.compile()

def run_workflow(state: IncidentState):
    app = build_graph()
    return app.invoke(state)

