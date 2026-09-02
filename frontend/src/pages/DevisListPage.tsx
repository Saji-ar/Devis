import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { DevisListItem } from '../types'

const euro = (n: number) => n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })

export default function DevisListPage() {
  const [items, setItems] = useState<DevisListItem[]>([])
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const load = () => api.listDevis().then(setItems).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const scan = async () => {
    setMsg(''); setError('')
    try {
      const r = await api.scan()
      setMsg(`Scan terminé : ${r.added} ajouté(s), ${r.updated} mis à jour, ${r.skipped} ignoré(s).`)
      load()
    } catch (e: any) { setError(e.message) }
  }

  const importer = async () => {
    setMsg(''); setError('')
    try {
      const r = await api.importOld()
      setMsg(`Import terminé : ${r.imported} devis importé(s)${r.refs.length ? ' — ' + r.refs.join(', ') : ''}.`)
      load()
    } catch (e: any) { setError(e.message) }
  }

  return (
    <div>
      <div className="toolbar">
        <h2 style={{ margin: 0 }}>Devis</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={importer} title="Importe les anciens devis .xlsx du dossier configuré">
            📥 Importer d'anciens devis
          </button>
          <button onClick={scan} title="Récupère les fichiers Excel créés ou modifiés à la main">
            🔄 Scanner le dossier Excel
          </button>
        </div>
      </div>
      {msg && <div className="muted" style={{ marginBottom: 10 }}>{msg}</div>}
      {error && <div className="error">{error}</div>}

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
                <td className="num"><Link to={`/devis/${it.devis.id}`}>Ouvrir →</Link></td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={6} className="muted">
                Aucun devis. Créez un client puis « + Devis », ou scannez le dossier Excel.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
