from typing import TypedDict, Optional, List, Dict


class IncidentState(TypedDict, total=False):
    description: str

    # Classification
    incident_type: str
    confidence: str
    explanation: str

    # RCA
    root_causes: List[Dict[str, str]]
    recommended_action: str
    rca_reason: str
