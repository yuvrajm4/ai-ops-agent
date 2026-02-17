from typing import TypedDict, Optional, List, Dict


class IncidentState(TypedDict, total=False):

    # -------------------------------
    # Core Incident Info
    # -------------------------------

    incident_id: str
    description: str
    source: str

    # -------------------------------
    # dbt Cloud Metadata
    # -------------------------------

    job_id: Optional[int]
    dbt_run_id: Optional[int]
    run_id: Optional[int]  # backward compatibility

    # -------------------------------
    # Model Metadata
    # -------------------------------

    model_name: Optional[str]
    unique_id: Optional[str]
    file_path: Optional[str]

    # -------------------------------
    # SQL Context
    # -------------------------------

    raw_sql: Optional[str]
    compiled_sql: Optional[str]

    # -------------------------------
    # Error Info
    # -------------------------------

    error_message: Optional[str]
    execution_time: Optional[float]

    # -------------------------------
    # Classification
    # -------------------------------

    incident_type: Optional[str]
    confidence: Optional[str]
    explanation: Optional[str]

    # -------------------------------
    # RCA Output
    # -------------------------------

    root_causes: List[Dict[str, str]]
    recommended_action: Optional[str]
    rca_reason: Optional[str]

    # -------------------------------
    # Impact Analysis
    # -------------------------------

    upstream_models: Optional[List[str]]
    downstream_models: Optional[List[str]]
    impacted_models: Optional[List[str]]
    blast_radius: Optional[int]

    missing_column: Optional[str]
    type_mismatch: Optional[Dict[str, str]]
