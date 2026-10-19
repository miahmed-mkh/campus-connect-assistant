import { useEffect, useRef, useState } from 'react'
import Header from '../components/Header'
import Message from '../components/Message'
import ChatInput from '../components/ChatInput'
import Suggestions from '../components/Suggestions'
import { sendMessage, sendFeedback } from '../services/api'
import { SUGGESTIONS } from '../data/mockResponses'

const STORAGE_KEY = 'campus-connect-history'

function now() {
  return new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

function newId() {
  return crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random())
}

function welcomeMessage() {
  return {
    id: 'welcome',
    role: 'bot',
    text: 'Bonjour 👋 Je suis l’assistant du campus ESIC. Posez-moi une question sur les horaires, les démarches, les formations ou la vie étudiante.',
    time: now(),
  }
}

// Historique conservé pendant la session du navigateur (US-002)
function loadSession() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY))
    if (saved?.sessionId && saved?.messages?.length) return saved
  } catch {
    /* sessionStorage indisponible : on repart de zéro */
  }
  return { sessionId: newId(), messages: [welcomeMessage()] }
}

export default function ChatPage({ user, onLogout, embedded = false }) {
  const [session, setSession] = useState(loadSession)
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  const { sessionId, messages } = session
  const hasUserMessages = messages.some((m) => m.role === 'user')

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    } catch {
      /* ignoré */
    }
  }, [session])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function addMessage(message) {
    setSession((s) => ({ ...s, messages: [...s.messages, message] }))
  }

  async function handleSend(text) {
    addMessage({ id: newId(), role: 'user', text, time: now() })
    setLoading(true)

    try {
      const data = await sendMessage(text, sessionId)
      addMessage({
        id: data.message_id || newId(),
        role: 'bot',
        text: data.answer,
        source: data.source,
        time: now(),
      })
    } catch {
      addMessage({
        id: newId(),
        role: 'bot',
        text: 'Le service est momentanément indisponible. Merci de réessayer dans quelques instants.',
        error: true,
        time: now(),
      })
    } finally {
      setLoading(false)
    }
  }

  async function handleFeedback(messageId, rating) {
    const previousMessage = messages.find((message) => message.id === messageId)
    const previousFeedback = previousMessage?.feedback

    setSession((currentSession) => ({
      ...currentSession,
      messages: currentSession.messages.map((message) =>
        message.id === messageId
          ? { ...message, feedback: rating }
          : message
      ),
    }))

    try {
      await sendFeedback(sessionId, messageId, rating)
    } catch {
      setSession((currentSession) => ({
        ...currentSession,
        messages: currentSession.messages.map((message) =>
          message.id === messageId
            ? { ...message, feedback: previousFeedback }
            : message
        ),
      }))
    }
  }

  // Redémarrer proprement la conversation (US-003)
  function handleReset() {
    setSession({ sessionId: newId(), messages: [welcomeMessage()] })
  }

  const chat = (
    <div
      className={
        embedded
          ? 'flex h-full flex-col overflow-hidden bg-slate-50'
          : 'flex h-full w-full max-w-3xl flex-col overflow-hidden bg-slate-50 shadow-lg sm:h-[90vh] sm:rounded-2xl'
      }
    >
      {!embedded && <Header user={user} onReset={handleReset} onLogout={onLogout} />}
      {embedded && (
        <div className="flex justify-end border-b border-slate-200 bg-white px-4 py-2">
          <button
            onClick={handleReset}
            className="rounded-lg border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
          >
            ↻ Recommencer
          </button>
        </div>
      )}

      <main className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((m) => (
          <Message key={m.id} message={m} onFeedback={handleFeedback} />
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-400">
              L’assistant écrit…
            </div>
          </div>
        )}

        {!hasUserMessages && !loading && (
          <div className="pt-2">
            <p className="mb-2 text-xs font-medium text-slate-500">Questions fréquentes</p>
            <Suggestions items={SUGGESTIONS} onSelect={handleSend} />
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  )

  if (embedded) return chat

  return (
    <div className="flex h-full items-center justify-center bg-slate-100 sm:p-4">{chat}</div>
  )
}
