FROM python:3.11-slim
WORKDIR /app
COPY app/backend/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY app/news_intelligence ./app/news_intelligence
COPY app/news_service ./app/news_service
CMD ["uvicorn","app.news_service.main:app","--host","0.0.0.0","--port","8010"]
