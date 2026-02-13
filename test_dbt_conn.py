from api.dbt_ingestor import extract_dbt_incidents
from graph.workflow import run_workflow

def main():
    incidents = extract_dbt_incidents()

    if not incidents:
        print("No dbt failures found.")
        return

    for incident in incidents:
        print("\n--- Processing Incident ---")
        final_state = run_workflow(incident)
        print("\nCLASSIFICATION AND RCA DONE")


if __name__ == "__main__":
    main()
