import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { Client, DevisListItem } from '../types'

const euro = (n: number) => n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })

export default function DevisListPage() {
  const [items, setItems] = useState<DevisListItem[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  // Formulaire "Nouveau devis"
  const [showNew, setShowNew] = useState(false)
  const [nom, setNom] = useState('')                     // nom du devis -> reference AAAA_nom
  const [clientId, setClientId] = useState<string>('')   // '' | '__new__' | id
  const [newNom, setNewNom] = useState('')
  const [newTel, setNewTel] = useState('')
  const [busy, setBusy] = useState(false)

  const fileRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const load = () => {
    api.listDevis().then(setItems).catch((e) => setError(e.message))
    api.listClients().then(setClients).catch(() => {})
  }
  useEffect(() => { load() }, [])

  const creerDevis = async () => {
    setError(''); setBusy(true)
    try {
      let cid: number
      if (clientId === '__new__') {
        if (!newNom.trim()) { setError('Nom du client obligatoire.'); setBusy(false); return }
        const c = await api.createClient({ nom: newNom.trim(), telephone: newTel.trim() || undefined })
        cid = c.id
      } else if (clientId) {
        cid = Number(clientId)
      } else {
        setError('Choisissez un client.'); setBusy(false); return
      }
      const d = await api.createDevis({ client_id: cid, nom: nom.trim() || undefined })
      navigate(`/devis/${d.id}`)
    } catch (e: any) { setError(e.message) } finally { setBusy(false) }
  }

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = '' // permet de re-déposer le même fichier
    if (!file) return
    setMsg(''); setError('')
    try {
      const r = await api.uploadDevis(file)
      setMsg(`Devis importé : ${r.reference}.`)
      navigate(`/devis/${r.devis_id}`)
    } catch (err: any) { setError(err.message) }
  }

  return (
    <div>
      <div className="toolbar">
        <h2 style={{ margin: 0 }}>Devis</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <input ref={fileRef} type="file" accept=".xlsx" hidden onChange={onFile} />
          <button onClick={() => fileRef.current?.click()}
            title="Importer un devis existant en déposant un fichier Excel .xlsx">
            📥 Importer un Excel
          </button>
          <button className="primary" onClick={() => setShowNew((v) => !v)}>+ Nouveau devis</button>
        </div>
      </div>
      {msg && <div className="muted" style={{ marginBottom: 10 }}>{msg}</div>}
      {error && <div className="error">{error}</div>}

      {showNew && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Nouveau devis</h3>
          <div className="field">
            <label>Nom du devis (sert de référence : 2026_nom)</label>
            <input value={nom} onChange={(e) => setNom(e.target.value)}
              placeholder="Mariage Dupont, Anniversaire 50 ans…" />
          </div>
          <div className="field">
            <label>Client</label>
            <select value={clientId} onChange={(e) => setClientId(e.target.value)}>
              <option value="">— Choisir un client —</option>
              <option value="__new__">➕ Nouveau client…</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
            </select>
          </div>
          {clientId === '__new__' && (
            <div className="row">
              <div className="field"><label>Nom du client *</label>
                <input value={newNom} onChange={(e) => setNewNom(e.target.value)} autoFocus /></div>
              <div className="field"><label>Téléphone</label>
                <input value={newTel} onChange={(e) => setNewTel(e.target.value)} /></div>
            </div>
          )}
          <button className="primary" onClick={creerDevis} disabled={busy}>
            {busy ? 'Création…' : 'Créer le devis'}
          </button>
        </div>
      )}

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Référence</th><th>Client</th><th>Objet</th>
              <th className="num">Versions</th><th className="num">Dernier TTC</th><th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.devis.id}>
                <td><Link to={`/devis/${it.devis.id}`}><strong>{it.devis.reference}</strong></Link></td>
                <td>{it.client?.nom}</td>
                <td className="muted">{it.devis.titre || '—'}</td>
                <td className="num">{it.nb_versions}</td>
                <td className="num">
                  {it.derniere_version ? euro(it.derniere_version.montant_ttc) : '—'}
                </td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>
                  {it.derniere_version && (
                    <button className="small" title="Ouvrir le PDF"
                      onClick={() => api.openPdf(it.derniere_version!.id).catch((e) => setError(e.message))}>
                      📄 PDF
                    </button>
                  )}{' '}
                  <Link to={`/devis/${it.devis.id}`}>Ouvrir →</Link>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={6} className="muted">
                Aucun devis. Cliquez « + Nouveau devis », ou importez un fichier Excel.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
