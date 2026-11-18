import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { Client, FactureListItem } from '../types'

const euro = (n: number) => n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
const today = () => new Date().toISOString().slice(0, 10)
const plus30 = () => new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10)

export default function FacturesListPage() {
  const [items, setItems] = useState<FactureListItem[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const [showNew, setShowNew] = useState(false)
  const [clientId, setClientId] = useState('')
  const [newNom, setNewNom] = useState('')
  const [dateFacture, setDateFacture] = useState(today())
  const [dateEcheance, setDateEcheance] = useState(plus30())
  const [busy, setBusy] = useState(false)

  const fileRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const load = () => {
    api.listFactures().then(setItems).catch((e) => setError(e.message))
    api.listClients().then(setClients).catch(() => {})
  }
  useEffect(() => { load() }, [])

  const creer = async () => {
    setError(''); setBusy(true)
    try {
      let cid: number
      if (clientId === '__new__') {
        if (!newNom.trim()) { setError('Nom du client obligatoire.'); setBusy(false); return }
        cid = (await api.createClient({ nom: newNom.trim() })).id
      } else if (clientId) { cid = Number(clientId) }
      else { setError('Choisissez un client.'); setBusy(false); return }
      const f = await api.createFacture({ client_id: cid, date_facture: dateFacture, date_echeance: dateEcheance })
      navigate(`/factures/${f.id}`)
    } catch (e: any) { setError(e.message) } finally { setBusy(false) }
  }

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; e.target.value = ''
    if (!file) return
    setMsg(''); setError('')
    try {
      const r = await api.uploadFacture(file)
      setMsg(`Facture importée : ${r.numero}.`)
      navigate(`/factures/${r.facture_id}`)
    } catch (err: any) { setError(err.message) }
  }

  const togglePaye = async (id: number, paye: boolean) => {
    try { await api.setPaye(id, paye); load() } catch (e: any) { setError(e.message) }
  }

  return (
    <div>
      <div className="toolbar">
        <h2 style={{ margin: 0 }}>Facturation</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <input ref={fileRef} type="file" accept=".xlsx" hidden onChange={onFile} />
          <button onClick={() => fileRef.current?.click()} title="Importer une facture .xlsx">📥 Importer un Excel</button>
          <button className="primary" onClick={() => setShowNew((v) => !v)}>+ Nouvelle facture</button>
        </div>
      </div>
      {msg && <div className="muted" style={{ marginBottom: 10 }}>{msg}</div>}
      {error && <div className="error">{error}</div>}

      {showNew && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Nouvelle facture</h3>
          <div className="field">
            <label>Client</label>
            <select value={clientId} onChange={(e) => setClientId(e.target.value)}>
              <option value="">— Choisir un client —</option>
              <option value="__new__">➕ Nouveau client…</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
            </select>
          </div>
          {clientId === '__new__' && (
            <div className="field"><label>Nom du client *</label>
              <input value={newNom} onChange={(e) => setNewNom(e.target.value)} autoFocus /></div>
          )}
          <div className="row">
            <div className="field"><label>Date de facture</label>
              <input type="date" value={dateFacture} onChange={(e) => setDateFacture(e.target.value)} /></div>
            <div className="field"><label>Échéance</label>
              <input type="date" value={dateEcheance} onChange={(e) => setDateEcheance(e.target.value)} /></div>
          </div>
          <button className="primary" onClick={creer} disabled={busy}>{busy ? 'Création…' : 'Créer la facture'}</button>
        </div>
      )}

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>N°</th><th>Client</th><th>Date</th><th className="num">TTC</th>
              <th>Statut</th><th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.facture.id}>
                <td><Link to={`/factures/${it.facture.id}`}><strong>{it.facture.numero}</strong></Link>
                  {it.devis_reference && <div className="muted">← {it.devis_reference}</div>}</td>
                <td>{it.client?.nom}</td>
                <td>{it.facture.date_facture}</td>
                <td className="num">{euro(it.facture.montant_ttc)}</td>
                <td>
                  <button className={`small badge ${it.facture.statut_paye ? 'app' : 'manuel'}`}
                    style={{ cursor: 'pointer', border: 'none' }}
                    onClick={() => togglePaye(it.facture.id, !it.facture.statut_paye)}>
                    {it.facture.statut_paye ? '✓ Payé' : 'Non payé'}
                  </button>
                </td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>
                  {it.has_pdf && (
                    <>
                      <button className="small" title="Télécharger le PDF"
                        onClick={() => api.downloadFile(`/factures/${it.facture.id}/pdf`, `Facture_${it.facture.numero}.pdf`).catch((e) => setError(e.message))}>
                        📄 PDF
                      </button>{' '}
                    </>
                  )}
                  <button className="small" title="Télécharger l'Excel"
                    onClick={() => api.downloadFile(`/factures/${it.facture.id}/xlsx`, `Facture_${it.facture.numero}.xlsx`).catch((e) => setError(e.message))}>
                    📊 Excel
                  </button>{' '}
                  <Link to={`/factures/${it.facture.id}`}>Ouvrir →</Link>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={6} className="muted">Aucune facture. « + Nouvelle facture », ou depuis un devis.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
