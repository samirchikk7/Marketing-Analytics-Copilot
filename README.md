# Marketing Analytics Copilot

Веб-приложение на Streamlit для маркетинговой аналитики: KPI, фильтры, дашборд, LLM-инсайты, A/B-гипотезы и подключение к внешним источникам.

## 1) Быстрый старт локально
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run Marketing-Analytics-copilot/app.py
```

Открой в браузере: `http://localhost:8501`.

## 2) Запуск через Docker
```bash
docker compose up --build
```

Открой: `http://localhost:8501`.

## 3) Как понять, применились ли изменения на GitHub
Изменения появляются на GitHub **только после push**.

Проверь и отправь:
```bash
git status
git log --oneline -n 5
git remote -v
git push origin <your-branch>
```

Если `git remote -v` пустой, сначала настрой remote:
```bash
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin <your-branch>
```

## 4) Как выложить как сайт (публичный URL)

### Вариант A: Streamlit Community Cloud (самый простой)
1. Запушь репозиторий в GitHub.
2. На share.streamlit.io выбери репозиторий и файл запуска:
   `Marketing-Analytics-copilot/app.py`.
3. В `Secrets` добавь при необходимости:
   - `META_ACCESS_TOKEN`
   - `META_AD_ACCOUNT_ID`
4. Нажми Deploy — получишь публичную ссылку.

### Важно про вкладку «Инсайты ИИ» в облаке
- По умолчанию в коде стоит `OLLAMA_URL=http://localhost:11434/api/chat`.
- На Streamlit Cloud `localhost` — это контейнер самого приложения, там обычно **нет запущенного Ollama**.
- Поэтому при нажатии «Сгенерировать инсайты» может быть `requests.exceptions.ConnectionError`.

Что делать:
1. Либо отключить/скрыть LLM-кнопки в облачной версии.
2. Либо подключить внешний endpoint и задать в Secrets:
   - `OLLAMA_URL=https://<your-endpoint>/api/chat`
   - `OLLAMA_MODEL=phi3` (или ваша модель)

### Вариант B: Render / Railway
- Подключи GitHub репозиторий.
- Команда запуска:
  `streamlit run Marketing-Analytics-copilot/app.py --server.address=0.0.0.0 --server.port=$PORT`
- Добавь переменные окружения для интеграций.

## 5) Источники данных в приложении
В сайдбаре доступны:
- Файл (CSV/XLSX)
- CSV/XLSX по URL
- JSON API
- Meta Ads (example API)

### Meta Ads
Нужны env-переменные:
- `META_ACCESS_TOKEN`
- `META_AD_ACCOUNT_ID`

Пример локально через Docker:
```bash
META_ACCESS_TOKEN=... META_AD_ACCOUNT_ID=... docker compose up --build
```


## 6) Можно ли подключить собственную LLM?
Да. Поддерживаются 2 режима через переменные окружения:

### Режим 1: локальная Ollama (по умолчанию)
```bash
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=phi3
```

### Режим 2: свой OpenAI-compatible endpoint
Подходит для self-hosted LLM шлюзов (например vLLM/TGI/LM Studio/OpenRouter-совместимый API).
```bash
LLM_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://<your-endpoint>/v1
OPENAI_MODEL=<your-model>
OPENAI_API_KEY=<your-key>
```

Для Streamlit Cloud эти переменные добавляются в **App → Settings → Secrets**.
