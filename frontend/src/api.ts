import type { Client, Devis, DevisData, DevisListItem, DevisVersion } from './types'

const BASE = '/api'
const TOKEN_KEY = 'devis_token'

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY) || '' },
  set token(v: string) { localStorage.setItem(TOKEN_KEY, v) },
  clear() { localStorage.removeItem(TOKEN_KEY) },
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', 'X-Auth-Token': auth.token },
    ...opts,
  })
  if (res.status === 401) {
    // Jeton invalide/expire : on efface et on recharge -> ecran de connexion.
    auth.clear()
    window.location.reload()
    throw new Error('Session expirée')
  }
  if (res.status === 423) {
    // Application bloquee : on recharge -> ecran de blocage.
    window.location.reload()
    throw new Error('Application bloquée')
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `Erreur ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Auth
  authStatus: () => req<{ auth_active: boolean; locked: boolean }>('/auth/status'),
  login: (password: string) =>
    req<{ token: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),

  // Clients
  listClients: () => req<Client[]>('/clients'),
  getClient: (id: number) => req<{ client: Client; devis: Devis[] }>(`/clients/${id}`),
  createClient: (c: Partial<Client>) =>
    req<Client>('/clients', { method: 'POST', body: JSON.stringify(c) }),
  updateClient: (id: number, c: Partial<Client>) =>
    req<Client>(`/clients/${id}`, { method: 'PATCH', body: JSON.stringify(c) }),
  deleteClient: (id: number) => req(`/clients/${id}`, { method: 'DELETE' }),

  // Devis
  listDevis: () => req<DevisListItem[]>('/devis'),
  createDevis: (d: { client_id: number; nom?: string; titre?: string }) =>
    req<Devis>('/devis', { method: 'POST', body: JSON.stringify(d) }),
  getDevis: (id: number) =>
    req<{ devis: Devis; client: Client; versions: DevisVersion[] }>(`/devis/${id}`),
  getVersionData: (versionId: number) => req<DevisData>(`/devis/version/${versionId}/data`),
  createVersion: (devisId: number, data: DevisData) =>
    req<DevisVersion>(`/devis/${devisId}/versions`, {
      method: 'POST',
      body: JSON.stringify({ data }),
    }),
  // Import d'un devis en deposant un fichier .xlsx
  uploadDevis: async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${BASE}/devis/import`, {
      method: 'POST', headers: { 'X-Auth-Token': auth.token }, body: fd,
    })
    if (res.status === 401) { auth.clear(); location.reload(); throw new Error('Session expirée') }
    if (!res.ok) {
      const d = await res.json().catch(() => ({}))
      throw new Error(d.detail || `Erreur ${res.status}`)
    }
    return res.json() as Promise<{ imported: number; reference: string; devis_id: number }>
  },

  // Telechargements authentifies (le jeton passe par l'en-tete, pas par l'URL).
  openPdf: async (versionId: number) => {
    const w = window.open('', '_blank') // ouvert AVANT l'await (sinon bloque par le navigateur)
    try {
      const res = await fetch(`${BASE}/devis/version/${versionId}/pdf`, {
        headers: { 'X-Auth-Token': auth.token },
      })
      if (res.status === 401) { auth.clear(); location.reload(); return }
      if (!res.ok) throw new Error('Erreur lors de la génération du PDF')
      const url = URL.createObjectURL(await res.blob())
      if (w) w.location.href = url; else window.location.href = url
    } catch (e) { if (w) w.close(); throw e }
  },
  downloadXlsx: async (versionId: number, filename: string) => {
    const res = await fetch(`${BASE}/devis/version/${versionId}/xlsx`, {
      headers: { 'X-Auth-Token': auth.token },
    })
    if (res.status === 401) { auth.clear(); location.reload(); return }
    if (!res.ok) throw new Error('Erreur de téléchargement')
    const url = URL.createObjectURL(await res.blob())
    const a = document.createElement('a')
    a.href = url; a.download = filename
    document.body.appendChild(a); a.click(); a.remove()
    URL.revokeObjectURL(url)
  },
}
