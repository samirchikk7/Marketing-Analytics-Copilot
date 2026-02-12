import os

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "phi3")

def ask_llm(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            "LLM-сервис недоступен. Проверь OLLAMA_URL/OLLAMA_MODEL и что Ollama запущен "
            "(на Streamlit Cloud localhost недоступен без внешнего endpoint)."
        ) from exc
