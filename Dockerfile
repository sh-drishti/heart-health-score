# The HHS API. Scores against the existing Python engine in the repo root.
#
# Build from the repo root, since the engine modules and data/ live there:
#   docker compose build api
#
# Python 3.14 to match what the dependency pins were tested against.
FROM python:3.14-slim

# WORKDIR must be the repo root: severity.py reads
# data/feature_mapping_hhs_2.xlsx at import time via a RELATIVE path, so the
# process will not start from anywhere else.
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Dependencies first, in their own layer, so code edits do not reinstall pandas.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Explicit allowlist rather than `COPY . .`, so the Streamlit apps and analysis
# scripts stay out of the image. These seven root modules are exactly what
# `import backend.main` pulls in:
COPY adapter.py assessment_service.py database.py hhs_v1_2_ui_app.py \
     mapping.py notification.py severity.py ./

# Referenced at import time by severity.py, and by the CSV patient source.
COPY data/ data/

# Bootstrapping the first admin on a fresh deploy:
#   docker compose exec api python seed_users.py --email ... --role admin
COPY seed_users.py ./

COPY backend/ backend/

# Drop privileges. Nothing in the image needs to be written at run time.
RUN useradd --create-home --shell /usr/sbin/nologin hhs \
    && chown -R hhs:hhs /app
USER hhs

EXPOSE 8000

# No curl in a slim image, so probe with the interpreter that is already here.
# Matches the unauthenticated /api/health route the app exposes for exactly this.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else sys.exit(1)"]

# One worker: ~124MB RSS each, and service._validations is still a
# process-local dict, so a second worker would see a different set of
# validations. Raise this only after that moves to a collection.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
