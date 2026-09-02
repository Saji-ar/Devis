import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import './index.css'
import App from './App'
import ClientsPage from './pages/ClientsPage'
import DevisListPage from './pages/DevisListPage'
import DevisEditorPage from './pages/DevisEditorPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/devis" replace /> },
      { path: 'clients', element: <ClientsPage /> },
      { path: 'devis', element: <DevisListPage /> },
      { path: 'devis/:id', element: <DevisEditorPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
