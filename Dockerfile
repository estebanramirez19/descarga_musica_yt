FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MUSICA_HOST=0.0.0.0 \
    MUSICA_PORT=8000

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py descargar_musica.py ./
COPY static ./static
COPY templates ./templates

EXPOSE 8000

CMD ["python", "app.py"]
