from typing import TypedDict, Optional, List

class IncidentState(TypedDict):
    incident_id: str
    description: str
    incident_type: Optional[str]
    suspected_root_cause: Optional[str]
    confidence: Optional[float]
    next_action: Optional[str]
    history: List[str]
