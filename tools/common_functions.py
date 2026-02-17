import json, requests, re, time
from typing import Optional, Dict, Any
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings

def get_llm():
    return Ollama(
        model="llama3",
        temperature=0.1
    )

def get_embeddings():
    return OllamaEmbeddings(
        model="nomic-embed-text"
    )


def parse_json(text: Optional[str]):
    """
    Safely parse JSON.
    Returns None if parsing fails.
    """
    if text is None:
        return None

    if not isinstance(text, str):
        return None

    text = text.strip()

    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

# HARDCODED FOR NOW

ACCOUNT_ID = "70471823532973"         
API_TOKEN = "dbtu_ZlIRcR8BMwnf_DWsBUVtXKF19WPExLBe4bW3w6Dln9-is8XiY8"
BASE_URL = "https://iy274.us1.dbt.com"

def get_failed_dbt_runs(limit=5):
    url = f"{BASE_URL}/api/v2/accounts/{ACCOUNT_ID}/runs/?limit=1"

    headers = {
        "Authorization": f"Token {API_TOKEN}",
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("❌ Failed fetching runs:", response.text)
        return []

    runs = response.json().get("data", [])
    print(f"Found {len(runs)} failed runs")

    return runs

def get_run_artifact(run_id, artifact_name):
    url = f"{BASE_URL}/api/v2/accounts/{ACCOUNT_ID}/runs/?limit=1"

    url = f"{BASE_URL}/api/v2/accounts/{ACCOUNT_ID}/runs/{run_id}/artifacts/{artifact_name}"

    headers = {
        "Authorization": f"Token {API_TOKEN}",
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Failed fetching artifact {artifact_name}")
        return None

    return response.json()


def retry_dbt_cloud_job(job_id: int, max_attempts: int = 2, delay_seconds: int = 15):
    """
    Retries a dbt Cloud job multiple times.
    Returns final result.
    """

    for attempt in range(1, max_attempts + 1):

        print(f"\n🔁 Attempt {attempt}/{max_attempts}")

        run_id = trigger_dbt_cloud_job(job_id)

        if not run_id:
            return {"success": False, "reason": "trigger_failed"}

        result = wait_for_dbt_run_completion(job_id, run_id)

        if result.get("success"):
            return {
                "success": True,
                "attempts": attempt,
                "run_id": run_id
            }

        if attempt < max_attempts:
            print(f"⏳ Waiting {delay_seconds}s before next attempt...")
            time.sleep(delay_seconds)

    return {
        "success": False,
        "attempts": max_attempts,
        "reason": "all_attempts_failed"
    }

def trigger_dbt_cloud_job(job_id: int, cause: str = "Triggered by AI Retry Agent") -> Optional[int]:
    """
    Triggers a dbt Cloud job run.
    Returns run_id if successful, else None.
    """

    url = f"{BASE_URL}/api/v2/accounts/{ACCOUNT_ID}/jobs/{job_id}/run/"

    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "cause": cause
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code not in (200, 201):
        print("❌ Failed triggering dbt job:", response.text)
        return None

    run_id = response.json().get("data", {}).get("id")
    print(f"✅ Triggered dbt Cloud run: {run_id}")

    return run_id


def get_dbt_run_status(job_id: int, run_id: int) -> str:
    """
    Fetch the current status of a dbt Cloud run.

    Args:
        run_id (int): The dbt Cloud run ID

    Returns:
        str: One of:
             queued | starting | running |
             success | error | cancelled |
             unknown
    """
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}/api/v2/accounts/{ACCOUNT_ID}/runs/{run_id}/"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch run status. "
            f"Status code: {response.status_code}, "
            f"Response: {response.text}"
        )

    data = response.json().get("data", {})
    status_code = data.get("status")

    # dbt Cloud numeric status mapping
    status_map = {
        1: "queued",
        2: "starting",
        3: "running",
        10: "success",
        20: "error",
        30: "cancelled"
    }

    return status_map.get(status_code, "unknown")


def wait_for_dbt_run_completion(job_id: int, run_id: int, poll_interval: int = 10, timeout: int = 900):

    print(f"⏳ Polling dbt run {run_id}...")

    start_time = time.time()

    while True:
        status = get_dbt_run_status(job_id, run_id)
        print(f"Current status: {status}")

        if status == "success":
            return {"success": True, "status": status}

        if status in ("error", "cancelled"):
            return {"success": False, "status": status}

        if time.time() - start_time > timeout:
            print("⏰ Polling timeout reached")
            return {"success": False, "status": "timeout"}

        time.sleep(poll_interval)


