import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { api, auth } from './api'

type Gate = 'loading' | 'locked' | 'login' | 'ok'

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--bg)' }}>
      <div className="panel" style={{ width: 340, maxWidth: '90vw' }}>{children}</div>
    </div>
  )
}

function Login({ onOk }: { onOk: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setBusy(true); setError('')
    try {
      const { token } = await api.login(password)
      auth.token = token
      onOk()
    } catch (e: any) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <Centered>
      <h2 style={{ marginTop: 0 }}>🍽️ Devis Traiteur</h2>
      <div className="field">
        <label>Mot de passe</label>
        <input type="password" value={password} autoFocus
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()} />
      </div>
      {error && <div className="error">{error}</div>}
      <button className="primary" onClick={submit} disabled={busy} style={{ width: '100%' }}>
        {busy ? 'Connexion…' : 'Se connecter'}
      </button>
    </Centered>
  )
}

export default function App() {
  const [gate, setGate] = useState<Gate>('loading')

  const check = async () => {
    try {
      const s = await api.authStatus()
      if (s.locked) return setGate('locked')
      if (!s.auth_active) return setGate('ok')       // aucune protection configuree
      setGate(auth.token ? 'ok' : 'login')
    } catch {
      setGate('login')
    }
  }
  useEffect(() => { check() }, [])

  if (gate === 'loading') return <Centered><div className="muted">Chargement…</div></Centered>

  if (gate === 'locked') return (
    <Centered>
      <h2 style={{ marginTop: 0 }}>🔒 Application bloquée</h2>
      <p className="muted">
        Trop de tentatives de connexion. Pour réactiver l'application, remettez
        <code> APP_ENABLED=true </code> dans le fichier <code>.env</code>, puis redémarrez le serveur.
      </p>
    </Centered>
  )

  if (gate === 'login') return <Login onOk={() => setGate('ok')} />

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>🍽️ Devis Traiteur</h1>
        <nav>
          <NavLink to="/devis" className={({ isActive }) => (isActive ? 'active' : '')}>Devis</NavLink>
          <NavLink to="/clients" className={({ isActive }) => (isActive ? 'active' : '')}>Clients</NavLink>
        </nav>
        <button className="small logout-btn"
          onClick={() => { auth.clear(); location.reload() }}>Se déconnecter</button>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
