# The HHS API. Scores against the existing Python engine in the repo root.
#
# Build from the repo root, since the engine modules and data/ live there:
#   docker compose build api
#
# Python 3.14 to match what the dependency pins were tested against.
FROM python:3.14-slim

# WORKDIR must be the repo root: data/cardio_hhs_2.csv is resolved by a
# RELATIVE path when source=csv is requested, so the process will not find it
# from anywhere else.
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Dependencies first, in their own layer, so code edits do not reinstall pandas.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# The engine modules, which live in the repo root. `import backend.main` needs
# six of them — adapter, assessment_service, database, hhs_v1_2_ui_app,
# mapping, notification — but we copy all the root modules rather than listing
# those six, so that adding a new import later does not break the container at
# startup.
#
# seed_users.py is the seventh and only other root module. It never runs on
# import; it bootstraps the first admin:
#   docker compose exec api python seed_users.py --email ... --role admin
COPY *.py ./

# data/cardio_hhs_2.csv backs the `source=csv` patient list. The spreadsheets
# alongside it no longer drive any code — they are kept as the written record of
# which clinical guideline each threshold came from.
COPY data/ data/

COPY backend/ backend/

# The additional-parameter collection programme. Its own top-level package, so
# it needs its own COPY — `COPY *.py ./` above matches root modules only, and
# leaving this out builds an image that starts, then dies on the import in
# backend/main.py. Delete this line with the programme.
COPY collection/ collection/

# Drop privileges. Nothing in the image needs to be written at run time.
RUN useradd --create-home --shell /usr/sbin/nologin hhs \
    && chown -R hhs:hhs /app
USER hhs

EXPOSE 8000

# No curl in a slim image, so probe with the interpreter that is already here.
# Matches the unauthenticated /api/health route the app exposes for exactly this.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else sys.exit(1)"]

# Two workers to match the 2 vCPU on a t3.micro/small; ~109MB each, measured.
# Safe now that validations are in Mongo rather than a per-process dict —
# backend/ holds no module-level mutable state, so workers share nothing.
# Override for a bigger box with `command:` in docker-compose.yml.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
