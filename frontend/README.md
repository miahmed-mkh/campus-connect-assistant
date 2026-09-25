# Frontend – Campus Connect

Interface de chat de l'assistant virtuel (React + Vite + Tailwind CSS).

## Lancer en local

```bash
cd frontend
npm install
npm run dev
```

Puis ouvrir http://localhost:5173

## Mode simulé / mode réel

Copier `.env.example` en `.env` :

- `VITE_USE_MOCK=true` : réponses simulées, le backend n'est pas nécessaire
- `VITE_USE_MOCK=false` : appels vers l'API FastAPI (`http://localhost:8000`, via le proxy Vite)

## Contrat d'API attendu (à valider avec le backend)

| Endpoint | Requête | Réponse |
|---|---|---|
| `POST /api/chat` | `{ "message": "...", "session_id": "..." }` | `{ "answer": "...", "source": "..." }` |
| `POST /api/feedback` | `{ "session_id": "...", "message_id": "...", "rating": "up" \| "down" }` | – |

## Structure

```
src/
├── App.jsx                  # Logique du chat (session, envoi, reset)
├── components/
│   ├── Header.jsx           # En-tête + bouton « Recommencer »
│   ├── Message.jsx          # Bulle de message + source + 👍👎
│   ├── ChatInput.jsx        # Zone de saisie
│   └── Suggestions.jsx      # Questions fréquentes cliquables
├── services/api.js          # Appels à l'API (ou mock)
└── data/mockResponses.js    # Réponses simulées + suggestions
```

## User stories couvertes (Sprint 1)

- US-001 : poser une question et recevoir une réponse
- US-002 : historique de la conversation pendant la session
- US-003 : redémarrer la conversation
- US-004 : affichage responsive mobile / desktop
- US-005 : suggestions de questions fréquentes
- (US-024, en avance sur le Sprint 2) : boutons 👍👎
