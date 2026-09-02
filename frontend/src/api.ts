import type { Client, Devis, DevisData, DevisListItem, DevisVersion } from './types'

const BASE = '/api'

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `Erreur ${res.status}`)
  }
  return res.json()
}

export const api = {
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
  createDevis: (d: { client_id: number; titre?: string }) =>
    req<Devis>('/devis', { method: 'POST', body: JSON.stringify(d) }),
  importOld: () => req<{ imported: number; refs: string[] }>('/devis/import-anciens', { method: 'POST' }),
  getDevis: (id: number) =>
    req<{ devis: Devis; client: Client; versions: DevisVersion[] }>(`/devis/${id}`),
  getVersionData: (versionId: number) => req<DevisData>(`/devis/version/${versionId}/data`),
  createVersion: (devisId: number, data: DevisData) =>
    req<DevisVersion>(`/devis/${devisId}/versions`, {
      method: 'POST',
      body: JSON.stringify({ data }),
    }),
  scan: () => req<{ added: number; updated: number; skipped: number }>('/devis/scan', { method: 'POST' }),

  // Fichiers (URLs directes)
  pdfUrl: (versionId: number) => `${BASE}/devis/version/${versionId}/pdf`,
  xlsxUrl: (versionId: number) => `${BASE}/devis/version/${versionId}/xlsx`,
}
