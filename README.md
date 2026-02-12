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
