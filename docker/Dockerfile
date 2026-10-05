# Development container for learning and local API/web work.
# Django runserver is not presented as a production WSGI server.
FROM python:3.12-slim

ARG APP_VERSION=unknown
LABEL org.opencontainers.image.title="DocAtDoor" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.description="Healthcare-at-home Django application (development image)"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_ENGINE=django.db.backends.mysql \
    DB_HOST=db \
    DB_PORT=3306 \
    DB_NAME=docatdoor \
    DB_USER=docatdoor

WORKDIR /srv/docatdoor
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN useradd --create-home appuser && \
    mkdir -p /srv/docatdoor/media /srv/docatdoor/protected_media && \
    chown -R appuser:appuser /srv/docatdoor
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
