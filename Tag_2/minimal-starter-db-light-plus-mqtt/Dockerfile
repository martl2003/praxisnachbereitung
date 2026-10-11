FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends       curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host \"$API_HOST\" --port \"$API_CONTAINER_PORT\" --reload"]