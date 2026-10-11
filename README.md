# campus-connect-assistant
Assistant virtuel éducatif pour campus connecté, NLP, analytics et simulation IoT

Assistant virtuel educatif ESIC : chatbot campus (FAQ, procedures,
contacts, emploi du temps, reglement) avec journalisation anonymisee,
securite des entrees et collecte de feedback.

## Demarrage rapide

1. Copier `.env.example` vers `.env` et adapter si besoin.
2. `docker compose up -d postgres`
3. `python -m alembic upgrade head`
4. `uvicorn backend.app.main:app --reload` (API sur http://127.0.0.1:8000, documentation sur /docs)
5. `cd frontend && npm install && npm run dev` (interface sur http://localhost:5173)

## Tests

```bash
docker compose up -d postgres
python -m pytest backend/tests -q
```

Les tests s'executent sur une base PostgreSQL dediee, isolee de la base
de developpement : par defaut `campus_connect_test`, derivee de
`DATABASE_URL` (suffixe `_test`). Elle est creee et migree (Alembic)
automatiquement par `backend/tests/conftest.py`, et les tables sont
videes apres chaque test. La variable optionnelle `TEST_DATABASE_URL`
permet de forcer une autre base ; son nom doit se terminer par `_test`.
