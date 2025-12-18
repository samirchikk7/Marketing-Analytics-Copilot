import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "phi3"  # ту же модель, что ты pull-нул

def ask_llm(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]
