import json
import re
from typing import Optional, Dict, Any
from langchain_community.llms import Ollama

def get_llm():
    return Ollama(
        model="llama3",
        temperature=0.1
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
