FROM python:3.12-slim

WORKDIR /enki

COPY services/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /enki

ENV PYTHONPATH=/enki \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENKI_DATA_DIR=/data

EXPOSE 8000

# First start: create the root key and admin device in /data (only if missing),
# create the database tables (idempotent), then serve the API.
CMD ["sh", "-c", "python scripts/init_node.py && python -c 'from storage.postgres.db import initialize_schema; initialize_schema()' && uvicorn services.api.src.main:app --host 0.0.0.0 --port 8000"]
