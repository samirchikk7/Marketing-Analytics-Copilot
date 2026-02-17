FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Marketing-Analytics-copilot ./Marketing-Analytics-copilot

EXPOSE 8501

CMD ["streamlit", "run", "Marketing-Analytics-copilot/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
