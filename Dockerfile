FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app_hamoud

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc netcat-openbsd ca-certificates openssl \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app_hamoud/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app_hamoud/
