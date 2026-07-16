FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache tzdata

RUN adduser -D -g '' appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

USER appuser

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.main"]
