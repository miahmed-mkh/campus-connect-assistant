# Campus Connect Assistant

Assistant virtuel éducatif pour un campus connecté (ESIC) : un chatbot qui répond aux questions des étudiants sur la FAQ, les procédures administratives, les contacts, l'emploi du temps et le règlement, avec journalisation anonymisée des conversations, sécurisation des entrées, collecte de feedback et tableau de bord analytique.

Projet transverse réalisé en méthode Scrum (2ᵉ année). Les données (FAQ, procédures, annuaire, emploi du temps, documents) sont **fictives**, à usage pédagogique uniquement.

## Fonctionnalités

- **Chat** (`POST /api/chat`) : réponse issue de la base de connaissances, avec catégorie, source, score de confiance, indicateur `resolved` et, si la question est ambiguë, des questions proposées (`suggestions`).
- **Base de connaissances** : FAQ, procédures, contacts, emploi du temps, documents (règlement, guides) chargés depuis `backend/data/`.
- **Recherche sémantique** : la FAQ est aussi interrogée par similarité de sens (Sentence-BERT multilingue), y compris pour les questions reformulées ou posées en anglais.
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
| NLP | Sentence-BERT multilingue (`sentence-transformers`, PyTorch CPU) |
| Base de données | PostgreSQL 16 |
| Tableau de bord | Grafana 11.3 (profil `full`, port 3000 sur 127.0.0.1) |
| Tests / CI | Pytest (336 tests), GitHub Actions |
| Conteneurs | Docker Compose (profil `full`), images `python:3.12-slim` et `nginx:alpine` |

## Sécurité

- Masquage des données personnelles **avant** écriture en base (aucune donnée brute conservée).
- Chatbot : identifiant de session anonyme, pas de compte pour les étudiants qui posent leurs questions, aucune donnée nominative conservée.
- Console IoT : comptes avec rôles, contrôlés côté serveur (mots de passe hachés PBKDF2-SHA256, jeton signé HMAC avec expiration, rôle étudiant refusé en `403`). Voir la section « Console IoT et comptes ».
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

Toute la pile (PostgreSQL, migrations, API, front servi par Nginx, Grafana) sans Python ni Node installés :

```bash
cp .env.example .env
docker compose --profile full up -d --build
```

Puis ouvrir http://localhost:8088/ (Swagger : http://localhost:8088/docs).

- `migrate` applique les migrations Alembic puis se termine ; `api` ne démarre qu'après son succès ; `web` attend que `api` soit saine.
- `api` n'est **pas publiée sur l'hôte** : seul Nginx est exposé et fait office de reverse proxy. Pas de CORS à gérer.
- Le port hôte se règle via `WEB_HOST_PORT` dans `.env` (8080 est souvent réservé par Windows, d'où 8088 par défaut).
- Grafana démarre aussi avec le profil `full` (http://localhost:3000). Après `cp .env.example .env`, remplacer `GRAFANA_ADMIN_PASSWORD` (valeur `change_me`) par un vrai mot de passe : voir la section « Tableau de bord Grafana ».
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

## Console IoT et comptes

La page `iot-console.html` permet de piloter les appareils simulés à la main. En démo Docker, elle est servie par Nginx : `http://localhost:8088/iot-console.html`.

Elle propose trois fonctions :

- **Capteur de salle** : curseurs de température, d'humidité et d'affluence, envoi manuel ou automatique toutes les 5 secondes.
- **Borne d'accueil** : questions au chatbot sur le canal `kiosk` et signal de présence toutes les 10 secondes.
- **Statut des appareils** : tableau rafraîchi toutes les 3 secondes, avec l'état en ligne ou hors ligne et les dernières mesures.

### Comptes et rôles

L'accès se fait par un compte. Les droits sont contrôlés **côté serveur** : masquer un bouton dans la page ne suffit pas, l'API refuse les requêtes non autorisées.

| Rôle | Droits |
|---|---|
| `responsable` | capteur, borne, statut |
| `intervenant` | capteur, borne, statut |
| `etudiant` | aucun pilotage : l'API répond `403` |

- Route de connexion : `POST /api/iot/console/login`.
- Mots de passe stockés **uniquement hachés** (PBKDF2-SHA256, 600 000 itérations, sel aléatoire).
- Jeton signé HMAC-SHA256, avec expiration (3600 secondes par défaut).
- Compte inconnu et mauvais mot de passe renvoient la même erreur `401`, avec un temps de réponse comparable.
- `CONSOLE_TOKEN_SECRET` vide : connexion désactivée (`503`).
- Jeton invalide ou expiré : `401`. Rôle sans droit : `403`.
- Les clés `X-Device-Key` et `X-Analytics-Key` restent valides pour les simulateurs et les scripts. Le jeton d'un compte ne donne pas accès à `GET /api/analytics/summary`.

### Configurer les comptes

Les comptes se définissent dans `.env` (ignoré par Git), jamais dans le dépôt. Les variables sont `CONSOLE_TOKEN_SECRET`, `CONSOLE_TOKEN_TTL_SECONDS`, `CONSOLE_RESPONSABLE_HASH`, `CONSOLE_INTERVENANT_HASH` et `CONSOLE_ETUDIANT_HASH`. Elles figurent, vides, dans `.env.example`.

Générer le secret de signature :

~~~bash
python -c "import secrets; print(secrets.token_hex(32))"
~~~

Générer le hachage d'un mot de passe, à coller dans la variable du rôle voulu :

~~~bash
python -m backend.scripts.hash_password
~~~

Après modification de `.env`, recréer l'API pour qu'elle relise les variables :

~~~bash
docker compose --profile full --profile iot up -d --build
~~~

Les mots de passe de démonstration ne figurent pas dans ce dépôt : ils sont communiqués séparément.

### Limites assumées de la console

- Pas de limitation du nombre d'essais sur la connexion : le coût du hachage PBKDF2 ralentit les attaques par force brute, mais un blocage après plusieurs échecs reste à ajouter.
- Le jeton de session est conservé dans le `sessionStorage` du navigateur : il disparaît à la fermeture de l'onglet, mais une faille XSS pourrait le lire.
- Les comptes sont définis par variables d'environnement : pas de gestion en ligne (création, changement de mot de passe, révocation d'un jeton avant son expiration).
- Pas de HTTPS en démonstration : les mots de passe circulent en clair sur le réseau local.
- Les mots de passe de démonstration sont des valeurs d'exemple, à remplacer pour tout autre usage.

## Consulter la base avec Adminer

Adminer est une interface web pour parcourir les tables PostgreSQL (sessions, messages, mesures IoT). Il est **optionnel** : il ne démarre qu'avec le profil Docker `tools`.

~~~bash
docker compose --profile tools up -d adminer
~~~

Ouvrir ensuite `http://localhost:8090` et remplir le formulaire :

| Champ | Valeur |
|---|---|
| Système | PostgreSQL |
| Serveur | `postgres` |
| Utilisateur | `POSTGRES_USER` du fichier `.env` |
| Mot de passe | `POSTGRES_PASSWORD` du fichier `.env` |
| Base de données | `campus_connect` |

- Le port est lié à `127.0.0.1` : Adminer n'est pas accessible depuis le réseau. Il se change avec `ADMINER_HOST_PORT`.
- Outil de développement et de démonstration : à ne pas lancer en production.

## Tableau de bord Grafana

Grafana affiche des statistiques d'usage lues directement dans la base PostgreSQL : questions posées, conversations, satisfaction, temps de réponse, catégories, questions les plus fréquentes, comptes créés, retours négatifs et état des bornes IoT.

### Lancement

Le service `grafana` appartient au profil `full` : il démarre avec la démo complète.

~~~bash
docker compose --profile full --profile iot up -d --build
~~~

- Adresse : `http://localhost:3000`, publiée uniquement sur `127.0.0.1`.
- Image : `grafana/grafana:11.3.0` (environ 650 Mo à télécharger la première fois).
- Dans l'espace admin (`http://localhost:8088`), l'onglet **Statistiques** affiche le tableau de bord dans un cadre, actualisé toutes les 30 secondes. Le bouton « Ouvrir en grand » l'ouvre dans un nouvel onglet.
- L'adresse de Grafana utilisée par le frontend peut être changée avec `VITE_GRAFANA_URL` (défaut : `http://localhost:3000`).

### Configuration

Définir dans le fichier `.env` (ignoré par Git) :

| Variable | Défaut dans `compose.yaml` | Rôle |
|---|---|---|
| `GRAFANA_ADMIN_USER` | `admin` | identifiant administrateur |
| `GRAFANA_ADMIN_PASSWORD` | `change_me` | mot de passe administrateur : **à remplacer** |
| `GRAFANA_HOST_PORT` | `3000` | port local |

Grafana applique l'identifiant et le mot de passe au premier démarrage de son volume `grafana_data`.

### Provisionnement automatique

- Source de données : `infrastructure/grafana/provisioning/datasources/postgres.yaml` (`Campus Connect DB`). Les identifiants PostgreSQL sont lus dans les variables d'environnement, pas écrits dans le fichier.
- Tableau de bord : `infrastructure/grafana/dashboards/campus-connect.json` (« Campus Connect – Analytics », 11 panneaux).
- Le panneau « Top 10 des questions » lit `content_redacted`, c'est-à-dire le texte déjà masqué. La table `users` n'est lue que par un comptage.

### Limites

- Grafana se connecte avec l'utilisateur principal de PostgreSQL. Un administrateur Grafana peut donc exécuter n'importe quelle requête sur la base, y compris sur la table `users`. Une mise en production demanderait un compte PostgreSQL en lecture seule limité aux tables nécessaires.
- L'affichage dans un cadre est autorisé (`GF_SECURITY_ALLOW_EMBEDDING`). Le tableau de bord a été vérifié avec une session Grafana ouverte ; sans connexion préalable, la page de connexion de Grafana peut apparaître dans le cadre (non testé).
- Le mot de passe par défaut `change_me` ne convient qu'à un essai local.
- Les journaux de Grafana contiennent quatre erreurs au démarrage : un plugin `xychart` enregistré deux fois, et deux dossiers de provisionnement absents (`plugins`, `alerting`) qui ne servent pas ici. Elles n'empêchent pas le fonctionnement.
- La CI ne démarre pas Grafana : le tableau de bord n'est pas couvert par les tests automatiques.

## LLM optionnel (Ollama)

Le moteur de recherche reste la source des réponses. Un petit modèle de langage local peut, **en option**, reformuler un passage déjà trouvé pour le rendre plus lisible. Cette fonction est **expérimentale et désactivée par défaut** : la démo principale n'en a pas besoin.

### Activation

Le service `ollama` appartient au profil Docker Compose `llm`. Il faut aussi `LLM_ENABLED=true` (syntaxe Bash), puis télécharger le modèle une seule fois (environ 1 Go, conservé dans le volume `ollama_data`) :

~~~bash
LLM_ENABLED=true docker compose --profile full --profile llm up -d --build
docker exec campus-ollama ollama pull qwen2.5:1.5b
~~~

Sans `LLM_ENABLED=true`, l'API ne contacte jamais Ollama, même si le conteneur tourne.

### Réglages

Variables définies dans `.env.example` et dans `compose.yaml` :

| Variable | Défaut | Rôle |
|---|---|---|
| `LLM_ENABLED` | `false` | active la reformulation |
| `LLM_BASE_URL` | `http://ollama:11434` | adresse d'Ollama sur le réseau interne Docker |
| `LLM_MODEL` | `qwen2.5:1.5b` | modèle utilisé |
| `LLM_TIMEOUT_SECONDS` | `8` | délai maximal avant retour à la réponse du moteur |
| `LLM_MAX_PASSAGE_CHARS` | `600` | taille maximale du passage envoyé au modèle |
| `LLM_KEEP_ALIVE` | `10m` | durée de maintien du modèle en mémoire |

### Fonctionnement

- Le moteur trouve d'abord le passage et sa catégorie, comme sans LLM.
- La reformulation n'est tentée que si le passage fait 600 caractères au plus et si la catégorie n'est ni `unknown`, ni `schedule`, ni `contact`, ni `procedure` (liste `LLM_EXCLUDED_CATEGORIES` dans `backend/app/api/chat.py`). Les emplois du temps, les contacts et les procédures en étapes doivent rester exacts.
- La question est masquée par `redact_personal_data` avant d'être envoyée au modèle.
- Le modèle reçoit une consigne stricte (n'utiliser que le passage, température 0).
- Retour automatique à la réponse du moteur si la fonction est désactivée, si Ollama est injoignable ou trop lent, si la réponse est vide, si le modèle indique ne pas avoir l'information, ou si elle contient des caractères CJK.
- Ollama n'est pas publié sur l'hôte : il n'est joignable que depuis le réseau interne `campus_backend`, et aucune question n'est envoyée à un service externe.

### Limites mesurées

Mesures sur la machine de développement (8 cœurs, sans configuration GPU) avec `qwen2.5:1.5b` :

- Le chargement du modèle prend environ 10,7 s lors du premier appel. Le premier appel via l'API dépasse donc souvent le délai de 8 s (mesuré : 8,4 s, puis retour à la réponse du moteur).
- Une fois le modèle chargé, la reformulation prend de 1,7 s à 6,2 s selon la longueur du passage.
- Sur « j'ai perdu ma carte », la reformulation a omis un cas (le vol) et introduit une formulation fautive.
- Sur la procédure « convention de stage », des étapes ont été perdues, d'où l'exclusion de la catégorie `procedure`.
- Les tests automatiques (`backend/tests/test_llm_service.py`, `backend/tests/test_chat_llm.py`) simulent Ollama. Ils vérifient les replis et le masquage, pas la qualité des réponses.
- L'appel au modèle a lieu pendant que la transaction de base de données est ouverte. Il faudrait le sortir de la transaction avant une mise en production.

## Recherche sémantique (Sentence-BERT)

Le moteur lexical compare les mots ; il confond des questions qui partagent la même tournure (« À quelle heure ouvre la bibliothèque ? » renvoyait les horaires de la scolarité) et ne comprend pas l'anglais. La recherche sémantique compare le **sens** : les questions de la FAQ sont transformées en vecteurs par un modèle multilingue, puis comparées à la question posée par similarité cosinus.

### Activation

- Docker : **activée par défaut** (`SEMANTIC_ENABLED=true`). Le modèle est téléchargé à la construction de l'image ; l'API démarre ensuite sans accès réseau (`HF_HUB_OFFLINE=1`).
- En local : `pip install -r backend/requirements-semantic.txt` puis `SEMANTIC_ENABLED=true` dans `.env`. Sans ces dépendances, ou avec `SEMANTIC_ENABLED=false`, le moteur lexical répond seul.

| Variable | Défaut | Rôle |
|---|---|---|
| `SEMANTIC_ENABLED` | `false` (code), `true` (Docker) | active la recherche sémantique |
| `SEMANTIC_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | modèle d'embeddings |

### Fonctionnement

- Au démarrage, le modèle est chargé et les questions de la FAQ sont encodées **en arrière-plan** (`backend/app/services/semantic_service.py`). L'API répond tout de suite ; tant que l'index n'est pas prêt, le moteur lexical répond seul.
- Seules les vraies questions sont indexées : les tags d'un ou deux mots (« déjeuner », « conseil ») attiraient des questions sans rapport.
- Seuil d'acceptation : similarité **≥ 0.7** (valeur du brief). En dessous, la réponse sémantique est ignorée.
- Le sémantique devient un candidat `semantic` du classement. Quand il est en désaccord avec la FAQ lexicale, il la remplace, sauf correspondance lexicale exacte (score 1.0). Quand ils sont d'accord, les deux restent en lice. Les autres sources (emploi du temps, contacts, procédures, documents) ne changent pas.
- Si le modèle ne peut pas être chargé, l'erreur est journalisée une fois et le moteur lexical prend le relais, sans nouvelle tentative.

### Résultats mesurés

Sur la machine de développement (CPU, sans GPU) :

| Question | Avant | Après |
|---|---|---|
| À quelle heure ouvre la bibliothèque ? | horaires de la scolarité (faux, 0.81) | horaires de la bibliothèque (0.85) |
| When does the library open? | aucune réponse | horaires de la bibliothèque (0.76) |
| How can I get a school certificate? | aucune réponse | certificat de scolarité (0.97) |
| contact scolarité, Bonjour, carte perdue | réponse correcte | inchangée |
| Questions hors sujet (hélicoptère, capitale de l'Australie) | aucune réponse | aucune réponse |

- Temps de réponse de `POST /api/chat` via Nginx : **90 ms en médiane** (10 requêtes, `127.0.0.1`).
- Chargement du modèle et encodage des 180 questions de référence : quelques secondes au démarrage, en arrière-plan.
- Les 320 tests existants passent aussi avec le vrai modèle activé.

### Limites

- Les réponses restent en français : la question anglaise est comprise, la réponse n'est pas traduite.
- Entre 0.55 et 0.7, le modèle hésite (« je veux faire un stage » : 0.67 sur la bonne réponse, « la BU » : 0.66 sur une mauvaise) : ces questions passent par la clarification ci-dessous plutôt que par une réponse directe.
- Seule la FAQ est indexée, pas les documents ni les procédures.
- Image de l'API plus lourde (PyTorch CPU et modèle d'environ 470 Mo) et environ 1 Go de mémoire vive pour l'API.
- Les tests automatiques (`backend/tests/test_semantic_service.py`) utilisent un encodeur simulé : ils vérifient la logique, pas la qualité du modèle.

### Clarification des questions ambiguës (US-018)

Quand **aucune** source n'a de réponse fiable, mais que le sémantique trouve des questions proches (score entre 0.55 et 0.7), le chatbot demande de préciser au lieu de répondre « je ne sais pas » :

~~~json
{
  "answer": "Je ne suis pas sûr d’avoir bien compris. Vouliez-vous dire :",
  "category": "clarification",
  "resolved": false,
  "suggestions": [
    "Comment obtenir une convention de stage ?",
    "Comment choisir entre stage et alternance ?"
  ]
}
~~~

- Le frontend affiche les suggestions en boutons sous le message ; un clic envoie la question, qui figure telle quelle dans la FAQ et obtient donc la réponse exacte.
- Au plus 3 suggestions, une par entrée de la FAQ, sous sa question principale.
- Plancher de 0.55 mesuré : à 0.5, « réserver un hélicoptère » proposait déjà la navette. Les salutations ne sont jamais proposées (« il fait beau » ressemble à « Bonjour »).
- Une réponse fiable d'une autre source n'est jamais remplacée par une clarification.
- Catégorie `clarification`, comptée comme **non résolue** dans les statistiques et Grafana ; le LLM ne la reformule pas.
- Le champ `suggestions` est toujours présent dans la réponse de `POST /api/chat` (liste vide hors clarification).

| Question | Suggestions proposées |
|---|---|
| je veux faire un stage, je fais comment ? | convention de stage ; stage ou alternance |
| c'est quand les exams | résultats des examens ; dates des examens ; durée des examens |
| il fait beau aujourd'hui | aucune (réponse « je ne sais pas » habituelle) |

## Tests

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
│   ├── tests/                # 336 tests Pytest
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

Hors périmètre de cette version, identifiées pour la suite : réponses en anglais, interface d'administration de la base de connaissances, vocal, supervision Prometheus/Grafana, tests de bout en bout et de charge, matériel réel (ESP32/Raspberry Pi) à la place du simulateur.
