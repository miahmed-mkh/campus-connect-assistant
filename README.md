# Campus Connect Assistant

Assistant virtuel éducatif pour un campus connecté (ESIC) : un chatbot qui répond aux questions des étudiants sur la FAQ, les procédures administratives, les contacts, l'emploi du temps et le règlement, avec journalisation anonymisée des conversations, sécurisation des entrées, collecte de feedback et tableau de bord analytique.

Projet transverse réalisé en méthode Scrum (2ᵉ année). Les données (FAQ, procédures, annuaire, emploi du temps, documents) sont **fictives**, à usage pédagogique uniquement.

## Fonctionnalités

- **Chat** (`POST /api/chat`) : réponse issue de la base de connaissances, avec catégorie, source, score de confiance et indicateur `resolved`.
- **Base de connaissances** : FAQ, procédures, contacts, emploi du temps, documents (règlement, guides) chargés depuis `backend/data/`.
- **Classement explicable** : chaque source produit un candidat (confiance, seuil, marge, priorité) ; le meilleur est retenu et le raisonnement est journalisé.
- **Journalisation anonymisée** : sessions et messages persistés en PostgreSQL ; les données personnelles (e-mails, téléphones, identifiants…) sont **masquées avant stockage**.
- **Sécurité des entrées** : validation et nettoyage des messages, limitation de débit (rate limiting) par session.
- **Feedback** (`POST /api/feedback`) : pouce haut / bas sur chaque réponse.
- **Analytics** (`GET /api/analytics/summary?days=30`) : volumes, taux de résolution, temps de réponse, satisfaction, répartition par catégorie et par source, série journalière. Protégé par la clé `X-Analytics-Key`.
- **IoT simulé** (`POST /api/iot/telemetry`, `GET /api/iot/status`) : borne d'accueil et capteurs de salle simulés, télémétrie stockée en base, état en ligne ou hors ligne, canal `kiosk` dans le chat et les statistiques.
- **Supervision** : `GET /health`, documentation OpenAPI sur `/docs`.

## Architecture

```
Navigateur ──> Nginx (web, :8088) ──> FastAPI (api, :8000, non publiée) ──> PostgreSQL (postgres)
                 │  sert le build React (Vite + Tailwind)                     ▲
                 └─ reverse proxy /api/, /docs, /openapi.json, /health         │
                                                     migrate (one-shot) : alembic upgrade head
```

| Couche | Technologies |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Base de données | PostgreSQL 16 |
| Tests / CI | Pytest (250 tests), GitHub Actions |
| Conteneurs | Docker Compose (profil `full`), images `python:3.12-slim` et `nginx:alpine` |

## Sécurité

- Masquage des données personnelles **avant** écriture en base (aucune donnée brute conservée).
- Identifiant de session anonyme, pas de compte utilisateur ni de donnée nominative.
- Validation stricte des entrées (longueur, contenu) et limitation de débit.
- Endpoint analytics protégé par clé d'API (comparaison à temps constant), désactivé si aucune clé n'est configurée.
- Télémétrie IoT protégée par une clé d'appareil distincte de la clé analytics (écriture seule), validation stricte des mesures (types, bornes, taille du lot).
- En production Docker : API non exposée sur l'hôte, une seule porte d'entrée (Nginx), en-têtes de sécurité, conteneurs non-root avec healthchecks.
- Secrets dans `.env` (ignoré par Git) ; `.env.example` ne contient que des valeurs de démonstration.

## Démarrage rapide (développement)

Prérequis : Python 3.12, Node 24, Docker.

```bash
cp .env.example .env                      # adapter mots de passe et ANALYTICS_API_KEY si besoin
python -m venv .venv && source .venv/Scripts/activate    # Linux/macOS : source .venv/bin/activate
pip install -r backend/requirements.txt
docker compose up -d postgres             # base PostgreSQL seule (port hôte 5433)
python -m alembic upgrade head            # migrations
uvicorn backend.app.main:app --reload     # API : http://127.0.0.1:8000  (Swagger : /docs)
```

Dans un second terminal :

```bash
cd frontend && npm install && npm run dev  # interface : http://localhost:5173 (proxy /api -> :8000)
```

Pour utiliser la vraie API plutôt que les réponses simulées, créer `frontend/.env` avec `VITE_USE_MOCK=false`.

## Démo Docker complète (une commande)

Toute la pile (PostgreSQL, migrations, API, front servi par Nginx) sans Python ni Node installés :

```bash
cp .env.example .env
docker compose --profile full up -d --build
```

Puis ouvrir http://localhost:8088/ (Swagger : http://localhost:8088/docs).

- `migrate` applique les migrations Alembic puis se termine ; `api` ne démarre qu'après son succès ; `web` attend que `api` soit saine.
- `api` n'est **pas publiée sur l'hôte** : seul Nginx est exposé et fait office de reverse proxy. Pas de CORS à gérer.
- Le port hôte se règle via `WEB_HOST_PORT` dans `.env` (8080 est souvent réservé par Windows, d'où 8088 par défaut).
- Arrêt : `docker compose --profile full down` (ajouter `-v` pour supprimer aussi la base).
- Pour ajouter les simulateurs IoT : renseigner `IOT_DEVICE_KEY` et `ANALYTICS_API_KEY` dans `.env` (vides par défaut, l'IoT est alors désactivé), puis `docker compose --profile full --profile iot up -d --build`. Voir la section « IoT simulé ».


Le workflow de développement reste inchangé : `docker compose up -d postgres` ne lance que la base.

## IoT simulé (bornes et capteurs)

Le projet inclut une chaîne IoT complète, **simulée par logiciel** : deux types d'appareils envoient des mesures à l'API, qui les stocke et expose leur état.

- **Borne d'accueil** (`kiosk-hall-01`) : envoie un signal de vie (`heartbeat`) et pose des questions au chatbot sur le canal `kiosk`, comme un visiteur.
- **Capteur de salle** (`sensor-b204`) : envoie température, humidité et affluence.

### Endpoints

| Méthode | Route | Protection | Rôle |
|---|---|---|---|
| `POST` | `/api/iot/telemetry` | en-tête `X-Device-Key` | un appareil dépose 1 à 50 mesures (réponse `202`) |
| `GET` | `/api/iot/status` | en-tête `X-Analytics-Key` | état des appareils : en ligne ou non, dernière mesure par type |

- Deux clés distinctes : les appareils peuvent **écrire** (`IOT_DEVICE_KEY`), seul le personnel peut **lire** (`ANALYTICS_API_KEY`).
- Clé absente côté serveur : `503` (fonction désactivée). Clé fausse ou manquante : `401`.
- Types de mesure autorisés : `temperature`, `humidity`, `occupancy`, `heartbeat`. L'identifiant d'appareil est contraint par une expression régulière. Tout le reste est rejeté en `422`.
- Chaque mesure garde deux horodatages : `recorded_at` (déclaré par l'appareil) et `received_at` (posé par le serveur).
- Un appareil est « en ligne » s'il a émis dans les `IOT_ONLINE_THRESHOLD_SECONDS` dernières secondes (120 par défaut).
- Le canal `kiosk` est aussi accepté par `POST /api/chat` ; `GET /api/analytics/summary` ventile les sessions par canal (`sessions.by_channel`).

### Lancer les simulateurs

En local (l'API doit tourner, avec `IOT_DEVICE_KEY` renseignée dans `.env`) :

~~~bash
python -m backend.scripts.iot.kiosk_simulator --role sensor --count 3 --interval 1 --device-key <cle>
python -m backend.scripts.iot.kiosk_simulator --role kiosk --count 3 --interval 1 --chat-every 1 --device-key <cle>
~~~

Avec Docker (les simulateurs tournent en continu dans deux conteneurs) :

~~~bash
docker compose --profile full --profile iot up -d --build
curl -s -H "X-Analytics-Key: <cle-analytics>" http://localhost:8088/api/iot/status
~~~

Les conteneurs `sensor` et `kiosk` ne reçoivent que la clé d'appareil : ni accès à la base, ni clé analytics.

### Limites assumées

- Appareils simulés : aucun matériel réel n'est branché.
- Une clé d'appareil partagée par tous les appareils (pas de clé par appareil), sans HTTPS.
- Pas de limitation de débit ni de purge automatique sur la télémétrie.

```bash
docker compose up -d postgres
python -m pytest backend/tests -q
```

Les tests s'exécutent sur une base PostgreSQL dédiée, isolée de la base de développement : par défaut `campus_connect_test`, dérivée de `DATABASE_URL` (suffixe `_test`). Elle est créée et migrée automatiquement par `backend/tests/conftest.py`, et les tables sont vidées après chaque test. La variable optionnelle `TEST_DATABASE_URL` permet de forcer une autre base ; son nom doit se terminer par `_test` (garde-fou).

La CI GitHub Actions (`.github/workflows/ci.yml`) s'exécute sur chaque push et pull request vers `develop` et `main` :

- job **backend** : PostgreSQL de service, `alembic upgrade head`, `alembic check`, `pytest` ;
- job **frontend** : `npm ci`, `npm run build`.

## Structure du dépôt

```
.
├── backend/
│   ├── alembic/              # migrations
│   ├── app/
│   │   ├── api/              # routes : chat, feedback, analytics
│   │   ├── core/             # configuration (pydantic-settings)
│   │   ├── db/               # engine, session, Base
│   │   ├── models/           # ConversationSession, Message, Feedback
│   │   ├── schemas/          # modèles Pydantic entrée/sortie
│   │   └── services/         # connaissances, classement, redaction PII, sécurité, rate limit, analytics
│   ├── data/                 # faq.json + knowledge_base/{raw,processed}
│   ├── scripts/knowledge_base/  # extraction PDF, normalisation, vérification des données
│   ├── tests/                # 250 tests Pytest
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React + Vite + Tailwind, Dockerfile multi-étapes, nginx.conf
├── .github/workflows/ci.yml
├── alembic.ini
├── compose.yaml
└── .env.example
```

## Organisation du travail

- Branche `develop` pour l'intégration, `main` pour les livraisons ; une branche `feature/*` par fonctionnalité, fusionnée par pull request après CI verte.
- Commits conventionnels (`feat:`, `fix:`, `test:`, `ci:`, `chore:`…).
- Suivi Scrum dans Jira (Epics : socle technique, conversation sécurisée, amélioration continue, base de connaissances, moteur de recherche, qualité & déploiement).

## Perspectives

Hors périmètre de cette version, identifiées pour la suite : compréhension du langage plus avancée (embeddings), interface d'administration de la base de connaissances, multilingue et vocal, supervision Prometheus/Grafana, tests de bout en bout et de charge, matériel réel (ESP32/Raspberry Pi) à la place du simulateur.
