export interface Client {
  id: number
  nom: string
  telephone?: string | null
  email?: string | null
  source?: string | null
  notes?: string | null
  created_at?: string
}

export interface Devis {
  id: number
  client_id: number
  reference: string
  titre?: string | null
  statut: string
  created_at?: string
}

export interface DevisVersion {
  id: number
  devis_id: number
  version_no: number
  date_version: string
  file_path: string
  montant_ht: number
  montant_tva: number
  montant_ttc: number
  origin: string
}

export interface LigneDevis {
  produit: string
  quantite: number
  prix_unit_ht: number
  tva_pct: number
}

export interface DevisData {
  date_devis: string
  date_prestation: string | null
  lignes: LigneDevis[]
}

export interface DevisListItem {
  devis: Devis
  client: Client
  nb_versions: number
  derniere_version: DevisVersion | null
}
