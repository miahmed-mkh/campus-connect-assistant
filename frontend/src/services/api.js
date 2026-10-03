import { getMockAnswer } from '../data/mockResponses'

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

/**
 * Envoie une question au chatbot.
 * Format attendu côté backend (à valider avec M1) :
 *   POST /api/chat  { message, session_id }
 *   → { answer, source }
 */
export async function sendMessage(message, sessionId) {
  if (USE_MOCK) {
    // Petit délai pour simuler le temps de réponse du serveur
    await new Promise((resolve) => setTimeout(resolve, 600))
    return getMockAnswer(message)
  }

  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  })

  if (!response.ok) {
    throw new Error(`Erreur serveur (${response.status})`)
  }
  return response.json()
}

/**
 * Envoie un feedback 👍 / 👎 sur une réponse.
 * Endpoint prévu : POST /api/feedback  { session_id, message_id, rating }
 */
export async function sendFeedback(sessionId, messageId, rating) {
  if (USE_MOCK) {
    console.log('[mock] feedback', { sessionId, messageId, rating })
    return
  }

  const response = await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message_id: messageId,
      rating,
    }),
  })

  if (!response.ok) {
    throw new Error(`Erreur serveur (${response.status})`)
  }

  return response.json()

}
