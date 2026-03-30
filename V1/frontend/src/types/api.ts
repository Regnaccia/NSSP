// ─── Enums ───────────────────────────────────────────────────────────────────

export type Ruolo = 'admin' | 'produzione' | 'logistica' | 'magazzino'

export type TipoProduzione = 'PEZZO' | 'BARRA' | 'FASCI'

export type StatoCommessa = 'in_coda' | 'in_produzione' | 'sospesa' | 'completata'

export type StatoMacchina = 'disponibile' | 'in_lavorazione' | 'in_setup' | 'in_manutenzione'

export type StatoSpedizione = 'in_preparazione' | 'spedita' | 'annullata'

export type TipoEvento = 'urgenza_formale' | 'ordine_pronto'

export type StatoEvento = 'aperto' | 'in_lavorazione' | 'risolto' | 'rifiutato'

export type FeedbackStato = 'accettata' | 'non_fattibile'

export type TipoPolicy = 'GIORNO_FISSO' | 'DATA_TASSATIVA' | 'SOGLIA_VALORE' | 'DEFAULT'

// ─── Response types (speculari agli schema Pydantic del backend) ──────────────

export interface UtenteResponse {
  id: string
  username: string
  ruolo: Ruolo
  attivo: boolean
  created_at: string
}

export interface ArticoloResponse {
  id: string
  codice: string
  codice_upper: string
  descrizione: string | null
  categoria: string | null
  capienza: number | null
  scorta_mensile: number
  mesi_scorta: number
  tipo_produzione: TipoProduzione
  lunghezza_barra: number | null
  multipli_taglio: number | null
  prd_pari: boolean
  storico_sufficiente: boolean
  scorta_calcolata_at: string | null
  synced_at: string
}

export interface CommessaResponse {
  id: string
  stato: StatoCommessa
  posizione_coda: number | null
  priorita_suggerita: 1 | 2 | null
  qty_cliente: number
  qty_scorta: number
  qty_prodotta_cliente: number
  qty_prodotta_scorta: number
  qty_totale: number
  qty_residua: number
  qty_ciclo_corrente: number | null
  riga_ordine_id: string | null
  articolo_id: string
  macchina_id: string | null
  codice_articolo: string
  descrizione_articolo: string | null
  macchina_codice: string | null
  numero_ordine: string | null
  created_at: string
  created_by: string | null
  sospesa_at: string | null
  sospesa_nota: string | null
  completata_at: string | null
  ldp_easyjob: string | null
}

export interface MacchinaResponse {
  id: string
  codice: string
  nome: string
  operazioni_eseguibili: string[]
  stato: StatoMacchina
  setup_corrente: string | null
  attiva: boolean
}

export interface EventoResponse {
  id: string
  tipo: TipoEvento
  mittente: string
  destinatario: string
  stato: StatoEvento
  ref_ordine_id: string | null
  numero_ordine: string | null
  cliente: string | null
  ref_commessa_id: string | null
  ref_articolo_id: string | null
  nota: string | null
  feedback_stato: FeedbackStato | null
  feedback_data_prevista: string | null
  feedback_nota: string | null
  corriere_override: string | null
  created_at: string
  updated_at: string
  resolved_at: string | null
}

export interface SpedizioneResponse {
  id: string
  ordine_id: string
  numero_ordine: string | null
  cliente: string | null
  tipo: 'totale' | 'parziale'
  stato: StatoSpedizione
  corriere: string | null
  data_pianificata: string | null
  data_spedizione: string | null
  colli: number | null
  peso_kg: number | null
  note: string | null
  created_at: string
}

export interface PolicyClienteResponse {
  id: string
  cliente_id: string
  tipo_policy: TipoPolicy
  giorno_fisso: number | null
  soglia_valore: number | null
  corriere_preferito: string | null
  note_spedizione: string | null
  policy_json: Record<string, unknown> | null
  configurata_da: string | null
  updated_at: string
}

// ─── Response types specifici per vista ──────────────────────────────────────

export interface RigaF1aResponse {
  riga_ordine_id: string
  ordine_id: string
  numero_ordine: string
  data_consegna: string | null
  flag_data_scaduta: boolean
  flag_urgenza: boolean
  codice_articolo: string
  descrizione_articolo: string | null
  cliente: string
  cliente_id: string
  qty_ordinata: number
  qty_disponibile: number
  qty_in_produzione: number
  giacenza_attuale: number
  qty_da_produrre: number
}

export interface ArticoloF1bResponse {
  articolo_id: string
  codice: string
  descrizione: string | null
  tipo_produzione: TipoProduzione
  scorta_mensile: number
  mesi_scorta: number
  target_scorta: number
  qty_disponibile_futura: number
  qty_da_produrre_scorta: number
  scorta_calcolata_at: string | null
}

export interface ArticoloApprontareItem {
  commessa_id: string
  articolo_id: string
  codice_articolo: string
  descrizione_articolo: string | null
  qty_prodotta_cliente: number
  qty_prodotta_scorta: number
  qty_totale: number
  gia_registrata: boolean
}

export interface OrdineApprontareResponse {
  ordine_id: string
  numero_ordine: string
  data_consegna: string | null
  cliente: string
  cliente_id: string
  flag_urgenza: boolean
  tutte_registrate: boolean
  articoli: ArticoloApprontareItem[]
}

export interface OrdineSpedireResponse {
  ordine_id: string
  numero_ordine: string
  data_consegna: string | null
  cliente: string
  cliente_id: string
  tipo_policy: TipoPolicy
  corriere_suggerito: string | null
  data_spedizione_suggerita: string | null
  soglia_raggiunta: boolean | null
  flag_urgenza: boolean
  evento_id: string
}

export interface CalendarioGiornoItem {
  data: string
  spedizioni: SpedizioneResponse[]
}

export interface SyncTabella {
  tabella: string
  last_sync_at: string | null
  last_error: string | null
  records_updated: number
  sync_duration_ms: number
}

export interface SyncStatusResponse {
  easyjob_connesso: boolean
  tabelle: SyncTabella[]
}

// ─── Request types ────────────────────────────────────────────────────────────

export interface GeneraCommessaRiga {
  riga_ordine_id: string
  qty_ciclo_corrente: number | null
  qty_scorta: number
}

export interface GeneraCommesseRequest {
  righe: GeneraCommessaRiga[]
  created_by: string
}

export interface GeneraCommesseResponse {
  commesse_create: number
  file_excel_base64: string
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  username: string
  ruolo: Ruolo
}

export interface TokenPayload {
  sub: string
  username: string
  ruolo: Ruolo
  exp: number
}

// ─── Cliente (usato in logistica) ─────────────────────────────────────────────

export interface ClienteResponse {
  id: string
  codice: string
  ragione_sociale: string
  nickname: string | null
  email: string | null
  telefono: string | null
  indirizzo: string | null
  synced_at: string
}
