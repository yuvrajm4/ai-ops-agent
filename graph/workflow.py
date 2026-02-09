from langgraph.graph import StateGraph
from state import IncidentState
from agents.incident_agent import classify_incident

def decide_next_step(state: IncidentState) -> str:
    if state["confidence"] and state["confidence"] > 0.7:
        return "end"
    return "end"  # placeholder for future nodes

def build_graph():
    graph = StateGraph(IncidentState)

    graph.add_node("classify", classify_incident)
    graph.add_node("decide", decide_next_step)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "decide")
    graph.set_finish_point("decide")

    return graph.compile()
