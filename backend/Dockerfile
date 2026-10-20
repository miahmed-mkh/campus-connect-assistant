FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependances d'abord (cache de build)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Recherche semantique : dependances + modele telecharge a la construction,
# pour que l'API demarre sans acces reseau. Hors de /app : le chown plus bas
# dupliquerait sinon le modele (~470 Mo) dans une nouvelle couche.
ENV HF_HOME=/opt/models
COPY backend/requirements-semantic.txt backend/requirements-semantic.txt
RUN pip install --no-cache-dir -r backend/requirements-semantic.txt \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', device='cpu')"
ENV HF_HUB_OFFLINE=1

# Code applicatif + configuration Alembic (racine)
COPY alembic.ini ./alembic.ini
COPY backend ./backend

# Utilisateur non-root
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
