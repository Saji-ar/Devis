import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { Client } from '../types'

const EMPTY = { nom: '', telephone: '', email: '', source: '', notes: '' }

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [form, setForm] = useState({ ...EMPTY })
  const [error, setError] = useState('')
  const [editId, setEditId] = useState<number | null>(null)
  const [edit, setEdit] = useState<Partial<Client>>({})
  const navigate = useNavigate()

  const load = () => api.listClients().then(setClients).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const create = async () => {
    setError('')
    if (!form.nom.trim()) { setError('Le nom est obligatoire.'); return }
    try {
      await api.createClient(form)
      setForm({ ...EMPTY })
      load()
    } catch (e: any) { setError(e.message) }
  }

  const startEdit = (c: Client) => { setEditId(c.id); setEdit({ ...c }) }
  const saveEdit = async () => {
    try {
      await api.updateClient(editId!, edit)
      setEditId(null); load()
    } catch (e: any) { setError(e.message) }
  }

  const nouveauDevis = async (client: Client) => {
    const d = await api.createDevis({ client_id: client.id })
    navigate(`/devis/${d.id}`)
  }

  return (
    <div>
      <h2>Clients</h2>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Nouveau client</h3>
        <div className="row">
          <div className="field"><label>Nom *</label>
            <input value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} /></div>
          <div className="field"><label>Téléphone</label>
            <input value={form.telephone} onChange={(e) => setForm({ ...form, telephone: e.target.value })} /></div>
        </div>
        <div className="row">
          <div className="field"><label>Email</label>
            <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          <div className="field"><label>Comment vous a-t-il connu ?</label>
            <input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}
              placeholder="Bouche-à-oreille, Instagram, mariage d'un ami..." /></div>
        </div>
        <div className="field"><label>Notes</label>
          <textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
        {error && <div className="error">{error}</div>}
        <button className="primary" onClick={create}>Ajouter le client</button>
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr><th>Nom</th><th>Téléphone</th><th>Source</th><th></th></tr>
          </thead>
          <tbody>
            {clients.map((c) => editId === c.id ? (
              <tr key={c.id}>
                <td><input value={edit.nom || ''} onChange={(e) => setEdit({ ...edit, nom: e.target.value })} /></td>
                <td><input value={edit.telephone || ''} onChange={(e) => setEdit({ ...edit, telephone: e.target.value })} /></td>
                <td><input value={edit.source || ''} onChange={(e) => setEdit({ ...edit, source: e.target.value })} /></td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>
                  <button className="small primary" onClick={saveEdit}>Enregistrer</button>{' '}
                  <button className="small" onClick={() => setEditId(null)}>Annuler</button>
                </td>
              </tr>
            ) : (
              <tr key={c.id}>
                <td><strong>{c.nom}</strong>{c.email && <div className="muted">{c.email}</div>}</td>
                <td>{c.telephone || '—'}</td>
                <td>{c.source || '—'}</td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>
                  <button className="small" onClick={() => startEdit(c)}>Éditer</button>{' '}
                  <button className="small primary" onClick={() => nouveauDevis(c)}>+ Devis</button>
                </td>
              </tr>
            ))}
            {clients.length === 0 && (
              <tr><td colSpan={4} className="muted">Aucun client pour l'instant.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
