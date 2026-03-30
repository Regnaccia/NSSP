export const POLLING_INTERVAL = {
  KIOSK: 15_000,  // 15s — terminali operativi
  OFFICE: 30_000, // 30s — viste ufficio
  SLOW: 60_000,   // 60s — sync status, calendario
} as const

export const STATI_COMMESSA = ['in_coda', 'in_produzione', 'sospesa', 'completata'] as const

export const GIORNI_SETTIMANA: Record<number, string> = {
  1: 'Lunedì', 2: 'Martedì', 3: 'Mercoledì', 4: 'Giovedì',
  5: 'Venerdì', 6: 'Sabato', 7: 'Domenica',
}

export const RUOLI = ['admin', 'produzione', 'logistica', 'magazzino'] as const

export const LABEL_RUOLO: Record<string, string> = {
  admin: 'Amministratore',
  produzione: 'Produzione',
  logistica: 'Logistica',
  magazzino: 'Magazzino',
}

export const LABEL_TIPO_POLICY: Record<string, string> = {
  DEFAULT: 'Default',
  DATA_TASSATIVA: 'Data tassativa',
  GIORNO_FISSO: 'Giorno fisso',
  SOGLIA_VALORE: 'Soglia valore',
}
