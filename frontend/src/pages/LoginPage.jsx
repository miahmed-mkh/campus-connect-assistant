import { useState } from 'react'
import { login, register } from '../services/auth'

const INPUT_CLASS =
  'w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

function Field({ id, label, ...props }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input id={id} className={INPUT_CLASS} required {...props} />
    </div>
  )
}

export default function LoginPage({ onLogin }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const isRegister = mode === 'register'

  function switchMode(next) {
    setMode(next)
    setError('')
    setPassword('')
    setConfirm('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (isRegister && password !== confirm) {
      setError('Les deux mots de passe ne correspondent pas.')
      return
    }

    setLoading(true)
    try {
      const user = isRegister
        ? await register(username.trim(), displayName.trim(), password)
        : await login(username.trim(), password)
      onLogin(user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-lg">
        <div className="mb-5 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-lg font-bold text-white">
            CC
          </div>
          <h1 className="text-lg font-semibold text-slate-800">Campus Connect</h1>
          <p className="text-sm text-slate-500">
            {isRegister ? 'Créez votre compte étudiant' : 'Connectez-vous pour accéder à l’assistant'}
          </p>
        </div>

        <div className="mb-5 grid grid-cols-2 rounded-xl bg-slate-100 p-1 text-sm">
          <button
            type="button"
            onClick={() => switchMode('login')}
            className={`rounded-lg py-1.5 ${!isRegister ? 'bg-white font-medium text-slate-800 shadow-sm' : 'text-slate-500'}`}
          >
            Se connecter
          </button>
          <button
            type="button"
            onClick={() => switchMode('register')}
            className={`rounded-lg py-1.5 ${isRegister ? 'bg-white font-medium text-slate-800 shadow-sm' : 'text-slate-500'}`}
          >
            Créer un compte
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <Field
              id="displayName"
              label="Nom et prénom"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="name"
              maxLength={100}
            />
          )}

          <Field
            id="username"
            label={isRegister ? 'Adresse e-mail' : 'E-mail ou identifiant'}
            type={isRegister ? 'email' : 'text'}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete={isRegister ? 'email' : 'username'}
            maxLength={254}
            autoFocus
          />

          <Field
            id="password"
            label="Mot de passe"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            minLength={isRegister ? 8 : undefined}
            maxLength={128}
          />

          {isRegister && (
            <>
              <Field
                id="confirm"
                label="Confirmer le mot de passe"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
              />
              <p className="-mt-2 text-xs text-slate-500">8 caractères minimum.</p>
            </>
          )}

          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-blue-600 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading
              ? 'Veuillez patienter…'
              : isRegister
                ? 'Créer mon compte'
                : 'Se connecter'}
          </button>
        </form>
      </div>
    </div>
  )
}
