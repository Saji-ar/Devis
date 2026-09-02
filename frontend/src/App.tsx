import { NavLink, Outlet } from 'react-router-dom'

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>🍽️ Devis Traiteur</h1>
        <nav>
          <NavLink to="/devis" className={({ isActive }) => (isActive ? 'active' : '')}>
            Devis
          </NavLink>
          <NavLink to="/clients" className={({ isActive }) => (isActive ? 'active' : '')}>
            Clients
          </NavLink>
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
