export interface Client {
  id: number
  nom: string
  telephone?: string | null
  email?: string | null
  adresse_1?: string | null
  adresse_2?: string | null
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
  has_pdf?: boolean
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
  has_pdf?: boolean
}

export interface Facture {
  id: number
  numero: string
  client_id: number
  devis_id?: number | null
  date_facture: string
  date_echeance?: string | null
  statut_paye: boolean
  montant_ht: number
  montant_tva: number
  montant_ttc: number
  origin: string
}

export interface FactureData {
  numero: string
  date_facture: string
  date_echeance: string | null
  date_prestation: string | null
  client_nom: string
  client_tel: string
  client_email: string
  lignes: LigneDevis[]
}

export interface FactureListItem {
  facture: Facture
  client: Client
  devis_reference: string | null
  has_pdf?: boolean
}
