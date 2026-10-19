import { useState } from 'react'
import Header from '../components/Header'
import ChatPage from './ChatPage'

// Adresse de Grafana (modifiable avec VITE_GRAFANA_URL)
const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3000'
const DASHBOARD_PATH = '/d/campus-connect/campus-connect-analytics?orgId=1&refresh=30s'

const TABS = [
  { id: 'stats', label: 'Statistiques' },
  { id: 'chat', label: 'Assistant' },
  { id: 'iot', label: 'Bornes IoT' },
  { id: 'kb', label: 'Base de connaissances' },
]

export default function AdminPage({ user, onLogout }) {
  const [tab, setTab] = useState('stats')

  return (
    <div className="flex h-full items-center justify-center bg-slate-100 sm:p-4">
      <div className="flex h-full w-full max-w-5xl flex-col overflow-hidden bg-slate-50 shadow-lg sm:h-[90vh] sm:rounded-2xl">
        <Header user={user} onLogout={onLogout} />

        <nav className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-white px-4">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`whitespace-nowrap border-b-2 px-3 py-2.5 text-sm ${
                tab === t.id
                  ? 'border-blue-600 font-medium text-blue-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              {t.label}
            </button>
          ))}
          <span className="ml-auto self-center whitespace-nowrap rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
            Espace admin
          </span>
        </nav>

        <div className="min-h-0 flex-1">
          {tab === 'stats' && (
            <section className="flex h-full flex-col">
              <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-white px-4 py-2">
                <p className="text-sm text-slate-600">Tableau de bord Grafana, mis à jour toutes les 30 secondes</p>
                <a
                  href={GRAFANA_URL + DASHBOARD_PATH}
                  target="_blank"
                  rel="noreferrer"
                  className="whitespace-nowrap rounded-lg border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
                >
                  Ouvrir en grand ↗
                </a>
              </div>
              <iframe
                title="Dashboard Campus Connect"
                src={GRAFANA_URL + DASHBOARD_PATH + '&kiosk'}
                className="min-h-0 w-full flex-1 border-0"
              />
            </section>
          )}

          {tab === 'chat' && <ChatPage user={user} embedded />}

          {tab === 'iot' && (
            <section className="p-6">
              <h2 className="mb-2 text-base font-semibold text-slate-800">Supervision des bornes</h2>
              <p className="mb-4 text-sm text-slate-600">
                La console IoT affiche l’état des bornes et les dernières mesures envoyées.
              </p>
              <a
                href="/iot-console.html"
                target="_blank"
                rel="noreferrer"
                className="inline-block rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                Ouvrir la console IoT
              </a>
            </section>
          )}

          {tab === 'kb' && (
            <section className="p-6">
              <h2 className="mb-2 text-base font-semibold text-slate-800">Base de connaissances</h2>
              <p className="text-sm text-slate-600">
                Bientôt : ajouter, modifier et supprimer des questions/réponses (T24).
              </p>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
