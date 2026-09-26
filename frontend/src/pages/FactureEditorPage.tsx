import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import type { Client, Facture, FactureData, LigneDevis } from '../types'

const euro = (n: number) => n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
function emptyLigne(): LigneDevis { return { produit: '', quantite: 1, prix_unit_ht: 0, tva_pct: 10 } }
function totaux(d: FactureData) {
  const ht = d.lignes.reduce((s, l) => s + l.quantite * l.prix_unit_ht, 0)
  const tva = d.lignes.reduce((s, l) => s + l.quantite * l.prix_unit_ht * (l.tva_pct / 100), 0)
  return { ht, tva, ttc: ht + tva }
}

export default function FactureEditorPage() {
  const { id } = useParams()
  const factureId = Number(id)
  const [facture, setFacture] = useState<Facture | null>(null)
  const [client, setClient] = useState<Client | null>(null)
  const [devisRef, setDevisRef] = useState<string | null>(null)
  const [data, setData] = useState<FactureData | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const load = async () => {
    const res = await api.getFacture(factureId)
    setFacture(res.facture); setClient(res.client); setDevisRef(res.devis_reference)
    setData(res.data)
  }
  useEffect(() => { load() }, [factureId])

  const setLigne = (i: number, patch: Partial<LigneDevis>) =>
    setData((d) => d && ({ ...d, lignes: d.lignes.map((l, j) => (j === i ? { ...l, ...patch } : l)) }))
  const addLigne = () => setData((d) => d && ({ ...d, lignes: [...d.lignes, emptyLigne()] }))
  const removeLigne = (i: number) => setData((d) => d && ({ ...d, lignes: d.lignes.filter((_, j) => j !== i) }))
  const moveLigne = (i: number, dir: -1 | 1) => setData((d) => {
    if (!d) return d
    const j = i + dir; if (j < 0 || j >= d.lignes.length) return d
    const l = [...d.lignes];[l[i], l[j]] = [l[j], l[i]]; return { ...d, lignes: l }
  })

  const save = async () => {
    if (!data) return
    setSaving(true); setError('')
    try { await api.saveFacture(factureId, data); await load() }
    catch (e: any) { setError(e.message) } finally { setSaving(false) }
  }

  const togglePaye = async () => {
    if (!facture) return
    try { const f = await api.setPaye(factureId, !facture.statut_paye); setFacture(f) }
    catch (e: any) { setError(e.message) }
  }

  if (!facture || !data) return <div className="muted">Chargement…</div>
  const t = totaux(data)

  return (
    <div>
      <div className="toolbar">
        <div>
          <h2 style={{ margin: 0 }}>Facture {facture.numero}</h2>
          <div className="muted">{client?.nom}{devisRef ? ` — issue du devis ${devisRef}` : ''}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className={`badge ${facture.statut_paye ? 'app' : 'manuel'}`}
            style={{ cursor: 'pointer', border: 'none', padding: '8px 14px' }} onClick={togglePaye}>
            {facture.statut_paye ? '✓ Payé' : 'Marquer payé'}
          </button>
          <button onClick={() => api.downloadFile(`/factures/${facture.id}/pdf`, `Facture_${facture.numero}.pdf`).catch((e) => setError(e.message))}>📄 PDF</button>
          <button onClick={() => api.downloadFile(`/factures/${facture.id}/xlsx`, `Facture_${facture.numero}.xlsx`).catch((e) => setError(e.message))}>📊 Excel</button>
          <button className="primary" onClick={save} disabled={saving}>{saving ? 'Enregistrement…' : '💾 Enregistrer'}</button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="panel">
        <div className="row">
          <div className="field"><label>Date de facture</label>
            <input type="date" value={data.date_facture} onChange={(e) => setData({ ...data, date_facture: e.target.value })} /></div>
          <div className="field"><label>Échéance</label>
            <input type="date" value={data.date_echeance || ''} onChange={(e) => setData({ ...data, date_echeance: e.target.value || null })} /></div>
          <div className="field"><label>Date de la prestation</label>
            <input type="date" value={data.date_prestation || ''} onChange={(e) => setData({ ...data, date_prestation: e.target.value || null })} /></div>
        </div>
      </div>

      <div className="panel">
        <div className="toolbar" style={{ marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>Produits</h3>
          <button className="small primary" onClick={addLigne}>+ Ajouter</button>
        </div>
        {data.lignes.length === 0 && <div className="muted">Aucun produit.</div>}
        {data.lignes.map((l, i) => (
          <div className="produit-card" key={i}>
            <div className="produit-head">
              <span className="produit-num">Produit #{i + 1}</span>
              <div className="produit-actions">
                <button className="small" onClick={() => moveLigne(i, -1)}>↑</button>
                <button className="small" onClick={() => moveLigne(i, 1)}>↓</button>
                <button className="small danger" onClick={() => removeLigne(i)}>✕</button>
              </div>
            </div>
            <textarea className="produit-nom" rows={Math.max(2, (l.produit.match(/\n/g)?.length || 0) + 1)}
              value={l.produit} onChange={(e) => setLigne(i, { produit: e.target.value })} placeholder={"Produit / prestation…"} />
            <div className="produit-champs">
              <label>Quantité<input type="number" inputMode="decimal" value={l.quantite} onChange={(e) => setLigne(i, { quantite: +e.target.value })} /></label>
              <label>Prix Unit HT<input type="number" inputMode="decimal" step="0.01" value={l.prix_unit_ht} onChange={(e) => setLigne(i, { prix_unit_ht: +e.target.value })} /></label>
              <label>TVA %<input type="number" inputMode="decimal" value={l.tva_pct} onChange={(e) => setLigne(i, { tva_pct: +e.target.value })} /></label>
              <div className="produit-total"><span>Total HT</span><strong>{euro(l.quantite * l.prix_unit_ht)}</strong></div>
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
    </div>
  )
}
