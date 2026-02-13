import json, requests, re
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

def get_failed_dbt_runs(limit=5):
    ACCOUNT_ID = "70471823532973"         
    API_TOKEN = "dbtu_1HT6Ss8N4ZRntiPhQSXMlftcRwKVBhBDX7zjA9trrT-BkPybO4"
    BASE_URL = "https://iy274.us1.dbt.com"
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
    ACCOUNT_ID = "70471823532973"         
    API_TOKEN = "dbtu_1HT6Ss8N4ZRntiPhQSXMlftcRwKVBhBDX7zjA9trrT-BkPybO4"
    BASE_URL = "https://iy274.us1.dbt.com"
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


