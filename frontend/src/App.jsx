import { useState } from 'react'
import LoginPage from './pages/LoginPage'
import ChatPage from './pages/ChatPage'
import AdminPage from './pages/AdminPage'
import { getStoredUser, isAdmin, logout } from './services/auth'

export default function App() {
  const [user, setUser] = useState(getStoredUser)

  function handleLogout() {
    logout()
    try {
      // On efface aussi la conversation pour le prochain utilisateur
      sessionStorage.removeItem('campus-connect-history')
    } catch {
      /* ignoré */
    }
    setUser(null)
  }

  if (!user) {
    return <LoginPage onLogin={setUser} />
  }

  if (isAdmin(user)) {
    return <AdminPage user={user} onLogout={handleLogout} />
  }

  return <ChatPage user={user} onLogout={handleLogout} />
}
