FROM python:3.11-slim

WORKDIR /app

# dependências de sistema mínimas para xgboost/scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data/raw data/uploads modelos

EXPOSE 8000

# Servidor de produção (gunicorn). Em dev, "python app.py" já sobe com reload manual.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "120", "app:app"]
