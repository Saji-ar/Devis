import { useEffect, useState } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import { api } from '../api'
import type { Client, Devis, DevisData, DevisVersion, LigneDevis } from '../types'

const euro = (n: number) => n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
const today = () => new Date().toISOString().slice(0, 10)

function emptyData(): DevisData {
  return { date_devis: today(), date_prestation: null, lignes: [] }
}
function emptyLigne(): LigneDevis {
  return { produit: '', quantite: 1, prix_unit_ht: 0, tva_pct: 10 }
}

// Totaux calcules cote client (memes formules que le backend / le tableau Excel).
function totaux(d: DevisData) {
  const ht = d.lignes.reduce((s, l) => s + l.quantite * l.prix_unit_ht, 0)
  const tva = d.lignes.reduce((s, l) => s + l.quantite * l.prix_unit_ht * (l.tva_pct / 100), 0)
  return { ht, tva, ttc: ht + tva }
}

export default function DevisEditorPage() {
  const { id } = useParams()
  const location = useLocation()
  const devisId = Number(id)
  const [devis, setDevis] = useState<Devis | null>(null)
  const [client, setClient] = useState<Client | null>(null)
  const [versions, setVersions] = useState<DevisVersion[]>([])
  const [data, setData] = useState<DevisData>(emptyData())
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const load = async () => {
    const res = await api.getDevis(devisId)
    setDevis(res.devis)
    setClient(res.client)
    setVersions(res.versions)
    if (res.versions.length > 0) {
      const d = await api.getVersionData(res.versions[0].id)
      setData({ ...d, date_devis: today() }) // repart de la derniere version, datee du jour
    } else {
      // Nouveau devis : preremplit la date de prestation saisie a la creation.
      const dp = (location.state as { datePrestation?: string } | null)?.datePrestation
      setData({ ...emptyData(), date_prestation: dp || null })
    }
  }
  useEffect(() => { load() }, [devisId])

  const setLigne = (i: number, patch: Partial<LigneDevis>) =>
    setData((d) => ({ ...d, lignes: d.lignes.map((l, j) => (j === i ? { ...l, ...patch } : l)) }))
  const addLigne = () => setData((d) => ({ ...d, lignes: [...d.lignes, emptyLigne()] }))
  const removeLigne = (i: number) =>
    setData((d) => ({ ...d, lignes: d.lignes.filter((_, j) => j !== i) }))
  const moveLigne = (i: number, dir: -1 | 1) =>
    setData((d) => {
      const j = i + dir
      if (j < 0 || j >= d.lignes.length) return d
      const l = [...d.lignes]
      ;[l[i], l[j]] = [l[j], l[i]]
      return { ...d, lignes: l }
    })

  const chargerVersion = async (v: DevisVersion) => {
    const d = await api.getVersionData(v.id)
    setData({ ...d, date_devis: today() })
  }

  const save = async () => {
    setSaving(true); setError('')
    try {
      await api.createVersion(devisId, data)
      await load()
    } catch (e: any) { setError(e.message) } finally { setSaving(false) }
  }

  const t = totaux(data)
  if (!devis) return <div className="muted">Chargement…</div>

  return (
    <div>
      <div className="toolbar">
        <div>
          <h2 style={{ margin: 0 }}>Devis {devis.reference}</h2>
          <div className="muted">{client?.nom}{devis.titre ? ` — ${devis.titre}` : ''}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {versions.length > 0 && (
            <button onClick={() => api.downloadPdf(versions[0].id,
              `${devis.reference}_v${versions[0].version_no}.pdf`).catch((e) => setError(e.message))}
              title="Télécharger le PDF de la dernière version">📄 PDF</button>
          )}
          <button className="primary" onClick={save} disabled={saving}>
            {saving ? 'Enregistrement…' : '💾 Enregistrer une nouvelle version'}
          </button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="panel">
        <div className="row">
          <div className="field"><label>Date du devis</label>
            <input type="date" value={data.date_devis}
              onChange={(e) => setData({ ...data, date_devis: e.target.value })} /></div>
          <div className="field"><label>Date de la prestation</label>
            <input type="date" value={data.date_prestation || ''}
              onChange={(e) => setData({ ...data, date_prestation: e.target.value || null })} /></div>
        </div>
      </div>

      <div className="panel">
        <div className="toolbar" style={{ marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>Produits</h3>
          <button className="small primary" onClick={addLigne}>+ Ajouter</button>
        </div>

        {data.lignes.length === 0 && (
          <div className="muted">Aucun produit. Cliquez « + Ajouter ».</div>
        )}

        {data.lignes.map((l, i) => (
          <div className="produit-card" key={i}>
            <div className="produit-head">
              <span className="produit-num">Produit #{i + 1}</span>
              <div className="produit-actions">
                <button className="small" onClick={() => moveLigne(i, -1)} title="Monter">↑</button>
                <button className="small" onClick={() => moveLigne(i, 1)} title="Descendre">↓</button>
                <button className="small danger" onClick={() => removeLigne(i)} title="Supprimer">✕</button>
              </div>
            </div>
            <textarea className="produit-nom"
              rows={Math.max(2, (l.produit.match(/\n/g)?.length || 0) + 1)}
              value={l.produit} onChange={(e) => setLigne(i, { produit: e.target.value })}
              placeholder={"Formule repas buffet\n- Entrée...\n- Plat...\n- Dessert..."} />
            <div className="produit-champs">
              <label>Quantité
                <input type="number" inputMode="decimal" value={l.quantite}
                  onChange={(e) => setLigne(i, { quantite: +e.target.value })} /></label>
              <label>Prix Unit HT
                <input type="number" inputMode="decimal" step="0.01" value={l.prix_unit_ht}
                  onChange={(e) => setLigne(i, { prix_unit_ht: +e.target.value })} /></label>
              <label>TVA %
                <input type="number" inputMode="decimal" value={l.tva_pct}
                  onChange={(e) => setLigne(i, { tva_pct: +e.target.value })} /></label>
              <div className="produit-total">
                <span>Total HT</span>
                <strong>{euro(l.quantite * l.prix_unit_ht)}</strong>
              </div>
            </div>
          </div>
        ))}

        <button className="small" style={{ marginTop: 4 }} onClick={addLigne}>+ Ajouter un produit</button>

        <div className="totaux" style={{ marginTop: 16 }}>
          <div>Montant Total HT : {euro(t.ht)}</div>
          <div>Montant Total TVA : {euro(t.tva)}</div>
          <div className="ttc">Montant Total TTC : {euro(t.ttc)}</div>
        </div>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Historique des versions</h3>
        <table>
          <thead>
            <tr><th>Version</th><th>Date</th><th>Origine</th><th className="num">TTC</th><th></th></tr>
          </thead>
          <tbody>
            {versions.map((v) => (
              <tr key={v.id}>
                <td><strong>v{v.version_no}</strong></td>
                <td>{v.date_version}</td>
                <td><span className={`badge ${v.origin}`}>{v.origin}</span></td>
                <td className="num">{euro(v.montant_ttc)}</td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>
                  <button className="small" onClick={() => api.downloadPdf(v.id, `${devis.reference}_v${v.version_no}.pdf`).catch((e) => setError(e.message))}>PDF</button>{' '}
                  <button className="small" onClick={() => api.downloadXlsx(v.id, `${devis.reference}_v${v.version_no}.xlsx`).catch((e) => setError(e.message))}>Excel</button>{' '}
                  <button className="small" onClick={() => chargerVersion(v)}>Repartir de là</button>
                </td>
              </tr>
            ))}
            {versions.length === 0 && (
              <tr><td colSpan={5} className="muted">Aucune version. Remplissez le formulaire puis « Enregistrer ».</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
