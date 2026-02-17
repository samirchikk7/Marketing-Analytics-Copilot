import os

import requests


def _ask_ollama(prompt: str) -> str:
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
    model_name = os.getenv("OLLAMA_MODEL", "phi3")

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    try:
        resp = requests.post(ollama_url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            "LLM-сервис недоступен. Проверь OLLAMA_URL/OLLAMA_MODEL и что Ollama запущен "
            "(на Streamlit Cloud localhost недоступен без внешнего endpoint)."
        ) from exc


def _ask_openai_compatible(prompt: str) -> str:
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Для провайдера openai_compatible нужно задать OPENAI_API_KEY.")

    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (requests.exceptions.RequestException, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Не удалось получить ответ от openai_compatible endpoint. "
            "Проверь OPENAI_BASE_URL/OPENAI_MODEL/OPENAI_API_KEY."
        ) from exc


def ask_llm(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

    if provider == "ollama":
        return _ask_ollama(prompt)
    if provider in {"openai", "openai_compatible"}:
        return _ask_openai_compatible(prompt)

    raise RuntimeError("Неизвестный LLM_PROVIDER. Используй: ollama или openai_compatible.")
