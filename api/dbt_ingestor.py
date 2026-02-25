from typing import List
from state import IncidentState
from tools.common_functions import get_failed_dbt_runs, get_run_artifact


def extract_dbt_incidents() -> List[IncidentState]:
    incidents: List[IncidentState] = []

    failed_runs = get_failed_dbt_runs(limit=1)

    for run in failed_runs:
        run_id = run.get("id")
        job_id = run.get("job_id") 
        print(job_id)  

        run_results = get_run_artifact(run_id, "run_results.json")
        manifest = get_run_artifact(run_id, "manifest.json")

        if not run_results or not manifest:
            continue

        for result in run_results.get("results", []):
            if result.get("status") != "error":
                continue

            unique_id = result.get("unique_id")
            node = manifest.get("nodes", {}).get(unique_id, {})

            status = result.get("status")
            error_message = result.get("message")

            # Fallback for compile-time failures
            if not error_message and status == "error":
                error_message = run.get("error")

            # Final fallback
            if not error_message:
                error_message = "Compile-time failure (no message in artifact)"

            state: IncidentState = {
                "description": error_message,
                "source": "dbt_cloud",
                "job_id": job_id,              # REQUIRED FOR RETRY
                "dbt_run_id": run_id,          # REQUIRED FOR ESCALATION
                "incident_id": f"{run_id}_{unique_id}",    # Useful for memory
                "model_name": node.get("name"),
                "unique_id": unique_id,
                "file_path": node.get("original_file_path"),
                "raw_sql": node.get("raw_code"),
                "compiled_sql": node.get("compiled_code"),
                # Error Info
                "error_message": error_message,
                "execution_time": result.get("execution_time"),
            }

            incidents.append(state)

    print(f"Extracted {len(incidents)} dbt incidents")
    return incidents
