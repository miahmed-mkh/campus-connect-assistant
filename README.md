
## Démo Docker complète (une commande)

Toute la pile (PostgreSQL, migrations Alembic, API FastAPI, front React servi par Nginx) peut être lancée sans Python ni Node installés :

```bash
cp .env.example .env          # si ce n'est pas déjà fait, puis adapter les mots de passe
docker compose --profile full up -d --build
```

Puis ouvrir http://localhost:8088/ (Swagger : http://localhost:8088/docs).

Fonctionnement :

- `migrate` applique les migrations Alembic puis se termine ; `api` ne démarre qu'après son succès.
- `api` n'est **pas publiée sur l'hôte** : seul Nginx (`web`) est exposé et sert de reverse proxy vers `/api/`, `/docs`, `/openapi.json` et `/health`. Une seule porte d'entrée, pas de CORS à gérer.
- `web` est construit en multi-étapes (build Vite avec `VITE_USE_MOCK=false`, puis image `nginx:alpine`).
- Les conteneurs tournent avec un utilisateur non-root et disposent de healthchecks.
- Le port hôte se règle via `WEB_HOST_PORT` dans `.env` (8080 est souvent réservé par Windows, d'où 8088 par défaut).

Arrêt : `docker compose --profile full down` (ajouter `-v` pour supprimer aussi la base).

Le workflow de développement reste inchangé : `docker compose up -d postgres` ne lance que la base, l'API et le front tournant en local.
