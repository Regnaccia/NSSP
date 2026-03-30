# MRS Frontend — Convenzioni di Sviluppo

**Versione:** 1.0 — Marzo 2026  
**Riferimento backend:** `01_SETUP.md`, `02_ARCHITECTURE.md`, `03_AUTH.md`, `04_API_REFERENCE.md`  
**Stack:** React 18 + TypeScript + TanStack Query + Zustand + Tailwind CSS + shadcn/ui

---

## Indice

1. [Struttura directory](#1-struttura-directory)
2. [Due mondi separati: Office e Kiosk](#2-due-mondi-separati-office-e-kiosk)
3. [Tipi TypeScript](#3-tipi-typescript)
4. [Client HTTP](#4-client-http)
5. [Autenticazione e store Zustand](#5-autenticazione-e-store-zustand)
6. [Pattern TanStack Query](#6-pattern-tanstack-query)
7. [Componenti condivisi](#7-componenti-condivisi)
8. [Layout](#8-layout)
9. [Gestione errori e feedback utente](#9-gestione-errori-e-feedback-utente)
10. [Naming e convenzioni codice](#10-naming-e-convenzioni-codice)
11. [Pagina template: F1a](#11-pagina-template-f1a)

---

## 1. Struttura directory

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Produzione/
│   │   │   ├── F1a.tsx          # Lancio ordini cliente
│   │   │   ├── F1b.tsx          # Lancio scorte
│   │   │   ├── F2.tsx           # Schedulazione (drag&drop)
│   │   │   └── F4.tsx           # Gestione urgenze (vista produzione)
│   │   ├── Logistica/
│   │   │   ├── F3a.tsx          # Da spedire
│   │   │   ├── F3b.tsx          # Spedizioni pianificate
│   │   │   ├── F3c.tsx          # Calendario spedizioni
│   │   │   ├── F4.tsx           # Gestione urgenze (vista logistica)
│   │   │   └── Clienti.tsx      # Clienti + policy
│   │   ├── Reparto/
│   │   │   ├── MacchinaSelect.tsx  # Selezione macchina all'avvio kiosk
│   │   │   └── KioskReparto.tsx    # Vista operatore reparto
│   │   └── Magazzino/
│   │       └── KioskMagazzino.tsx  # Vista operatore magazzino
│   ├── components/
│   │   ├── SyncIndicator.tsx
│   │   ├── UrgenzaBadge.tsx
│   │   ├── CommessaStatusBadge.tsx
│   │   ├── SpedizioneStatusBadge.tsx
│   │   ├── ClienteLabel.tsx
│   │   └── DataConsegnaLabel.tsx
│   ├── layouts/
│   │   ├── OfficeLayout.tsx     # Con sidebar + header (Produzione, Logistica)
│   │   └── KioskLayout.tsx      # Full-screen touch-first (Reparto, Magazzino)
│   ├── hooks/
│   │   ├── useSyncStatus.ts
│   │   ├── useCommesse.ts
│   │   ├── useOrdiniF1a.ts
│   │   └── useEventi.ts
│   ├── api/
│   │   ├── officeClient.ts      # Axios con JWT (Produzione, Logistica)
│   │   ├── kioskClient.ts       # Axios senza auth (Reparto, Magazzino)
│   │   └── index.ts             # Re-export
│   ├── store/
│   │   └── authStore.ts         # Zustand: token, username, ruolo
│   ├── types/
│   │   └── api.ts               # Tutti i tipi TypeScript derivati da 04_API_REFERENCE
│   └── lib/
│       ├── utils.ts             # cn(), formatData(), formatQty()
│       └── constants.ts         # STATI_COMMESSA, RUOLI, POLLING_INTERVAL
```

---

## 2. Due mondi separati: Office e Kiosk

Questa è la regola architetturale più importante del frontend. Il codice dei due mondi **non si mescola mai**.

| | Office | Kiosk |
|---|---|---|
| **Router backend** | `/api/produzione`, `/api/logistica`, `/api/eventi`, `/api/articoli`, `/api/auth`, `/api/sync` | `/api/reparto`, `/api/magazzino` |
| **Autenticazione** | JWT richiesto | Nessuna auth |
| **Client HTTP** | `officeClient` | `kioskClient` |
| **Layout** | `OfficeLayout` | `KioskLayout` |
| **Cartella pagine** | `pages/Produzione/`, `pages/Logistica/` | `pages/Reparto/`, `pages/Magazzino/` |
| **Font size base** | 14px (default Tailwind) | 18px (classe `text-lg` come base) |
| **Bottoni min-height** | 36px (default shadcn) | 56px — touch target obbligatorio |
| **Polling** | 30s dove specificato | 15s — operatori aspettano aggiornamenti rapidi |

**Regola concreta:** mai importare `officeClient` in una pagina `Reparto/` o `Magazzino/`. Mai usare `KioskLayout` in una pagina `Produzione/` o `Logistica/`.

---

## 3. Tipi TypeScript

**File:** `src/types/api.ts`

Questi tipi sono derivati direttamente da `04_API_REFERENCE.md — Tipi comuni`. Non vanno mai inventati o riformulati.

```typescript
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
  priorita_suggerita: 1 | 2 | null   // 1=urgente, 2=normale
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
```

---

## 4. Client HTTP

**File:** `src/api/officeClient.ts` — per Produzione e Logistica (con JWT)

```typescript
import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

export const officeClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Aggiunge automaticamente il token JWT ad ogni richiesta
officeClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Intercetta 401 → logout + redirect login
officeClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)
```

**File:** `src/api/kioskClient.ts` — per Reparto e Magazzino (no auth)

```typescript
import axios from 'axios'

// Client pulito, senza interceptor auth — usato solo per /api/reparto e /api/magazzino
export const kioskClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})
```

**Regola:** le funzioni API di ogni modulo importano **solo il client corretto** per il proprio mondo.

```typescript
// ✅ Corretto
// pages/Produzione/F1a.tsx → usa officeClient
// pages/Reparto/KioskReparto.tsx → usa kioskClient

// ❌ Mai fare
// pages/Reparto/KioskReparto.tsx → import { officeClient } from '@/api/officeClient'
```

---

## 5. Autenticazione e store Zustand

**File:** `src/store/authStore.ts`

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Ruolo, TokenPayload } from '@/types/api'

interface AuthState {
  token: string | null
  username: string | null
  ruolo: Ruolo | null
  isAuthenticated: boolean
  login: (token: string, username: string, ruolo: Ruolo) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      username: null,
      ruolo: null,
      isAuthenticated: false,
      login: (token, username, ruolo) =>
        set({ token, username, ruolo, isAuthenticated: true }),
      logout: () =>
        set({ token: null, username: null, ruolo: null, isAuthenticated: false }),
    }),
    { name: 'mrs-auth' }
  )
)

// Helper: decodifica payload JWT lato client (senza verifica firma)
// Usato solo per leggere username/ruolo — il controllo accesso vero è backend
export function parseTokenPayload(token: string): TokenPayload {
  const base64 = token.split('.')[1]
  return JSON.parse(atob(base64)) as TokenPayload
}
```

**Come usare il ruolo per nascondere elementi UI:**

```tsx
const { ruolo } = useAuthStore()

// Mostrare un bottone solo all'admin
{ruolo === 'admin' && <Button>Forza sync</Button>}

// Disabilitare un'azione per ruolo non autorizzato
<Button disabled={ruolo !== 'produzione' && ruolo !== 'admin'}>
  Genera commesse
</Button>
```

**Regola:** la visibilità/disabilitazione UI basata su ruolo è un aiuto all'operatore, **non un controllo di sicurezza**. Il backend rifiuta sempre le chiamate non autorizzate (403). Non replicare logiche di sicurezza nel frontend.

---

## 6. Pattern TanStack Query

### 6.1 Query (GET)

Pattern standard per ogni vista che legge dati dal backend:

```typescript
// src/hooks/useOrdiniF1a.ts
import { useQuery } from '@tanstack/react-query'
import { officeClient } from '@/api/officeClient'
import type { RigaF1aResponse } from '@/types/api'

interface F1aParams {
  clienteId?: string
  urgenzaOnly?: boolean
  dataDa?: string
  dataA?: string
}

export function useOrdiniF1a(params: F1aParams = {}) {
  return useQuery({
    queryKey: ['produzione', 'f1a', params],
    queryFn: async () => {
      const { data } = await officeClient.get<RigaF1aResponse[]>(
        '/api/produzione/f1a',
        { params: {
          cliente_id: params.clienteId,
          urgenza_only: params.urgenzaOnly,
          data_da: params.dataDa,
          data_a: params.dataA,
        }}
      )
      return data
    },
    refetchInterval: 30_000,  // polling 30s per viste operative
  })
}
```

### 6.2 Mutation (POST / PATCH / PUT)

Pattern standard per ogni azione che modifica dati:

```typescript
// Esempio: avvia commessa (kiosk reparto)
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { kioskClient } from '@/api/kioskClient'
import type { CommessaResponse } from '@/types/api'
import { toast } from 'sonner'

export function useAvviaCommessa(macchinaId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (commessaId: string) => {
      const { data } = await kioskClient.post<CommessaResponse>(
        `/api/reparto/commesse/${commessaId}/avvia`
      )
      return data
    },
    onSuccess: () => {
      // Invalida la coda della macchina corrente per forzare refresh
      queryClient.invalidateQueries({ queryKey: ['reparto', 'coda', macchinaId] })
      toast.success('Commessa avviata')
    },
    onError: (err: unknown) => {
      const message = extractApiError(err)
      toast.error(message)
    },
  })
}
```

### 6.3 Query key conventions

Le query key devono rispecchiare la gerarchia delle risorse:

```typescript
// ✅ Corretto — gerarchia chiara, invalidazione precisa possibile
['produzione', 'f1a']
['produzione', 'f1a', { urgenzaOnly: true }]
['produzione', 'coda']
['reparto', 'coda', macchinaId]
['reparto', 'commessa', commessaId]
['logistica', 'da-spedire']
['logistica', 'spedizioni', { stato: 'in_preparazione' }]
['logistica', 'calendario', { dataDa, dataA }]
['magazzino', 'da-approntare']
['eventi', { tipo: 'urgenza_formale' }]
['sync', 'status']

// ❌ Da evitare — chiavi piatte non invalidabili in modo selettivo
['f1a']
['commesse']
```

### 6.4 Polling — quando e quanto

| Vista | Intervallo | Motivazione |
|---|---|---|
| F1a (produzione) | 30s | Nuovi ordini syncati da EasyJob |
| Coda kiosk reparto | 15s | Operatore aspetta aggiornamenti rapidi |
| Da approntare (magazzino) | 15s | Idem |
| Calendario logistica | 60s | Cambia meno spesso |
| Sync status | 60s | Monitoraggio, non operativo |
| F2 schedulazione | 30s | Solo lettura iniziale, drag&drop è locale |

Impostare sempre `refetchInterval` nell'hook, non nella pagina, così il comportamento è consistente.

---

## 7. Componenti condivisi

Questi componenti vanno creati **prima** di sviluppare le pagine. Ogni pagina li usa; se non esistono vengono reinventati in modo inconsistente.

### 7.1 SyncIndicator

Mostra lo stato del sync con EasyJob. Presente in ogni pagina office.

```tsx
// src/components/SyncIndicator.tsx
import { useQuery } from '@tanstack/react-query'
import { officeClient } from '@/api/officeClient'
import type { SyncStatusResponse } from '@/types/api'
import { formatDistanceToNow } from 'date-fns'
import { it } from 'date-fns/locale'

export function SyncIndicator({ tabella }: { tabella: string }) {
  const { data } = useQuery({
    queryKey: ['sync', 'status'],
    queryFn: async () => {
      const { data } = await officeClient.get<SyncStatusResponse>('/api/sync/status')
      return data
    },
    refetchInterval: 60_000,
  })

  const tabStatus = data?.tabelle.find(t => t.tabella === tabella)
  if (!tabStatus?.last_sync_at) return null

  const minutesAgo = Math.floor(
    (Date.now() - new Date(tabStatus.last_sync_at).getTime()) / 60_000
  )

  const color =
    tabStatus.last_error ? 'text-red-500' :
    minutesAgo > 30 ? 'text-red-500' :
    minutesAgo > 10 ? 'text-yellow-500' :
    'text-green-500'

  const label = formatDistanceToNow(new Date(tabStatus.last_sync_at), {
    addSuffix: true,
    locale: it,
  })

  return (
    <span className={`text-xs ${color}`}>
      Sync {label}
      {tabStatus.last_error && ' · ⚠ errore'}
    </span>
  )
}
```

### 7.2 UrgenzaBadge

```tsx
// src/components/UrgenzaBadge.tsx
import { Badge } from '@/components/ui/badge'

interface Props {
  attiva: boolean
  className?: string
}

export function UrgenzaBadge({ attiva, className }: Props) {
  if (!attiva) return null
  return (
    <Badge variant="destructive" className={className}>
      URGENTE
    </Badge>
  )
}
```

### 7.3 CommessaStatusBadge

```tsx
// src/components/CommessaStatusBadge.tsx
import { Badge } from '@/components/ui/badge'
import type { StatoCommessa } from '@/types/api'

const CONFIG: Record<StatoCommessa, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  in_coda:       { label: 'In coda',       variant: 'secondary' },
  in_produzione: { label: 'In produzione', variant: 'default' },
  sospesa:       { label: 'Sospesa',       variant: 'destructive' },
  completata:    { label: 'Completata',    variant: 'outline' },
}

export function CommessaStatusBadge({ stato }: { stato: StatoCommessa }) {
  const { label, variant } = CONFIG[stato]
  return <Badge variant={variant}>{label}</Badge>
}
```

### 7.4 SpedizioneStatusBadge

```tsx
// src/components/SpedizioneStatusBadge.tsx
import { Badge } from '@/components/ui/badge'
import type { StatoSpedizione } from '@/types/api'

const CONFIG: Record<StatoSpedizione, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
  in_preparazione: { label: 'In preparazione', variant: 'secondary' },
  spedita:         { label: 'Spedita',         variant: 'default' },
  annullata:       { label: 'Annullata',       variant: 'outline' },
}

export function SpedizioneStatusBadge({ stato }: { stato: StatoSpedizione }) {
  const { label, variant } = CONFIG[stato]
  return <Badge variant={variant}>{label}</Badge>
}
```

### 7.5 ClienteLabel

Gestisce la logica nickname || ragione_sociale che il backend risolve già nei join, ma a volte serve anche client-side.

```tsx
// src/components/ClienteLabel.tsx
interface Props {
  cliente: string | null   // campo già risolto (nickname || ragione_sociale) dal backend
  className?: string
}

export function ClienteLabel({ cliente, className }: Props) {
  return (
    <span className={className}>
      {cliente ?? '—'}
    </span>
  )
}
```

### 7.6 DataConsegnaLabel

Evidenzia date scadute o imminenti.

```tsx
// src/components/DataConsegnaLabel.tsx
import { format, isPast, isWithinInterval, addDays } from 'date-fns'
import { it } from 'date-fns/locale'
import { cn } from '@/lib/utils'

interface Props {
  data: string | null
  flagScaduta?: boolean
  className?: string
}

export function DataConsegnaLabel({ data, flagScaduta, className }: Props) {
  if (!data) return <span className={cn('text-muted-foreground', className)}>—</span>

  const date = new Date(data)
  const scaduta = flagScaduta ?? isPast(date)
  const imminente = !scaduta && isWithinInterval(date, { start: new Date(), end: addDays(new Date(), 3) })

  return (
    <span className={cn(
      scaduta ? 'text-red-600 font-semibold' :
      imminente ? 'text-yellow-600 font-medium' :
      'text-foreground',
      className
    )}>
      {format(date, 'd MMM yyyy', { locale: it })}
      {scaduta && ' ⚠'}
    </span>
  )
}
```

---

## 8. Layout

### 8.1 OfficeLayout

Per tutte le pagine di Produzione e Logistica. Ha sidebar di navigazione, header con username/ruolo e `SyncIndicator`.

```tsx
// src/layouts/OfficeLayout.tsx
import { Outlet, NavLink } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { SyncIndicator } from '@/components/SyncIndicator'

const NAV_PRODUZIONE = [
  { to: '/produzione/f1a', label: 'Lancio ordini' },
  { to: '/produzione/f1b', label: 'Lancio scorte' },
  { to: '/produzione/f2',  label: 'Schedulazione' },
  { to: '/produzione/f4',  label: 'Urgenze' },
]

const NAV_LOGISTICA = [
  { to: '/logistica/f3a',    label: 'Da spedire' },
  { to: '/logistica/f3b',    label: 'Spedizioni' },
  { to: '/logistica/f3c',    label: 'Calendario' },
  { to: '/logistica/f4',     label: 'Urgenze' },
  { to: '/logistica/clienti', label: 'Clienti' },
]

export function OfficeLayout() {
  const { username, ruolo, logout } = useAuthStore()
  const nav = ruolo === 'logistica' ? NAV_LOGISTICA : NAV_PRODUZIONE

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-56 border-r flex flex-col gap-1 p-4">
        <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
          MRS
        </div>
        {nav.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
        <div className="mt-auto pt-4 border-t">
          <SyncIndicator tabella="ordini" />
          <div className="text-xs text-muted-foreground mt-2">{username} · {ruolo}</div>
          <button
            onClick={logout}
            className="text-xs text-muted-foreground hover:text-foreground mt-1"
          >
            Logout
          </button>
        </div>
      </aside>

      {/* Contenuto pagina */}
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
```

### 8.2 KioskLayout

Per Reparto e Magazzino. Full-screen, font più grande, niente sidebar, niente logout — il terminale è sempre aperto.

```tsx
// src/layouts/KioskLayout.tsx
import { Outlet } from 'react-router-dom'

export function KioskLayout() {
  return (
    <div className="min-h-screen bg-background text-lg">
      {/* Nessun header complesso — i terminali kiosk sono always-on */}
      <Outlet />
    </div>
  )
}
```

---

## 9. Gestione errori e feedback utente

### 9.1 Estrazione errore API

Il backend usa sempre `{ "detail": "messaggio" }` per gli errori. Questa funzione va usata in tutti gli `onError`:

```typescript
// src/lib/utils.ts
export function extractApiError(err: unknown): string {
  if (
    err &&
    typeof err === 'object' &&
    'response' in err &&
    err.response &&
    typeof err.response === 'object' &&
    'data' in err.response &&
    err.response.data &&
    typeof err.response.data === 'object' &&
    'detail' in err.response.data
  ) {
    return String((err.response.data as { detail: string }).detail)
  }
  return 'Errore imprevisto — riprovare'
}
```

### 9.2 Pattern toast

Usare `sonner` (già incluso in shadcn/ui). Pattern uniforme per tutta l'app:

```typescript
// ✅ Azione completata
toast.success('Commessa avviata')
toast.success('Spedizione registrata')

// ✅ Errore business logic (409 dal backend)
toast.error('Transizione non consentita: la commessa non è in coda')

// ✅ Errore di rete / imprevisto
toast.error('Errore di connessione — riprovare')

// ✅ Operazione lunga (es. genera commesse con download)
const toastId = toast.loading('Generazione commesse...')
// ... dopo la mutation
toast.dismiss(toastId)
toast.success(`${result.commesse_create} commesse create`)
```

### 9.3 Codici HTTP da gestire esplicitamente

| Codice | Situazione | Risposta UI |
|---|---|---|
| 401 | Token scaduto | Redirect automatico a `/login` (interceptor) |
| 403 | Ruolo non autorizzato | `toast.error('Non autorizzato')` |
| 404 | Risorsa non trovata | `toast.error('Elemento non trovato')` |
| 409 | Conflitto business logic | `toast.error(detail)` — il messaggio backend è già leggibile |
| 500 | Errore interno | `toast.error('Errore del server — contattare l\'amministratore')` |

### 9.4 Stato loading / error nelle pagine

Usare sempre i dati di `isLoading` e `isError` da TanStack Query:

```tsx
const { data, isLoading, isError } = useOrdiniF1a()

if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
if (isError) return <div className="p-6 text-red-500">Errore nel caricamento dati</div>
if (!data?.length) return <div className="p-6 text-muted-foreground">Nessun elemento da mostrare</div>
```

---

## 10. Naming e convenzioni codice

### 10.1 File

| Tipo | Convention | Esempio |
|---|---|---|
| Pagine | PascalCase | `F1a.tsx`, `KioskReparto.tsx` |
| Componenti | PascalCase | `UrgenzaBadge.tsx` |
| Hook | camelCase con prefisso `use` | `useOrdiniF1a.ts`, `useCommesse.ts` |
| Store Zustand | camelCase con suffisso `Store` | `authStore.ts` |
| Client API | camelCase con suffisso `Client` | `officeClient.ts` |
| Tipi | `types/api.ts` unico file |  |
| Utilità | camelCase | `utils.ts`, `constants.ts` |

### 10.2 Costanti

```typescript
// src/lib/constants.ts

export const POLLING_INTERVAL = {
  KIOSK: 15_000,    // 15s — terminali operativi
  OFFICE: 30_000,   // 30s — viste ufficio
  SLOW: 60_000,     // 60s — sync status, calendario
} as const

export const STATI_COMMESSA = ['in_coda', 'in_produzione', 'sospesa', 'completata'] as const

export const GIORNI_SETTIMANA: Record<number, string> = {
  1: 'Lunedì', 2: 'Martedì', 3: 'Mercoledì', 4: 'Giovedì',
  5: 'Venerdì', 6: 'Sabato', 7: 'Domenica',
}
```

### 10.3 Download file Excel

Il backend restituisce il file Excel come base64 in `GeneraCommesseResponse.file_excel_base64`. Pattern da usare sempre quando serve scaricare il file:

```typescript
function downloadExcel(base64: string, filename: string) {
  const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0))
  const blob = new Blob([bytes], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
```

### 10.4 Formattazione date e quantità

```typescript
// src/lib/utils.ts
import { format } from 'date-fns'
import { it } from 'date-fns/locale'

// Date ISO string → "12 apr 2026"
export function formatData(isoString: string | null): string {
  if (!isoString) return '—'
  return format(new Date(isoString), 'd MMM yyyy', { locale: it })
}

// Quantità → con separatore migliaia
export function formatQty(n: number): string {
  return n.toLocaleString('it-IT')
}

// Peso → "12,5 kg"
export function formatPeso(kg: number | null): string {
  if (kg === null) return '—'
  return `${kg.toLocaleString('it-IT')} kg`
}
```

---

## 11. Pagina template: F1a

Questa è la pagina di riferimento. Claude Code deve seguire questa struttura per tutte le pagine `Produzione/` e `Logistica/`.

```tsx
// src/pages/Produzione/F1a.tsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { useOrdiniF1a } from '@/hooks/useOrdiniF1a'
import { officeClient } from '@/api/officeClient'
import { useAuthStore } from '@/store/authStore'

import { UrgenzaBadge } from '@/components/UrgenzaBadge'
import { DataConsegnaLabel } from '@/components/DataConsegnaLabel'
import { SyncIndicator } from '@/components/SyncIndicator'
import { ClienteLabel } from '@/components/ClienteLabel'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'

import { extractApiError, downloadExcel, formatQty } from '@/lib/utils'
import type { GeneraCommesseRequest, GeneraCommesseResponse } from '@/types/api'

export default function F1a() {
  const { username } = useAuthStore()
  const queryClient = useQueryClient()

  // ── Stato locale UI ──────────────────────────────────────────────────────
  const [righeSelezionate, setRigheSelezionate] = useState<Set<string>>(new Set())

  // ── Fetch dati ───────────────────────────────────────────────────────────
  const { data: righe, isLoading, isError } = useOrdiniF1a()

  // ── Mutation ─────────────────────────────────────────────────────────────
  const generaCommesse = useMutation({
    mutationFn: async (payload: GeneraCommesseRequest) => {
      const { data } = await officeClient.post<GeneraCommesseResponse>(
        '/api/produzione/genera-commesse',
        payload
      )
      return data
    },
    onSuccess: (result) => {
      // Invalida F1a (le righe processate spariscono) e la coda produzione
      queryClient.invalidateQueries({ queryKey: ['produzione', 'f1a'] })
      queryClient.invalidateQueries({ queryKey: ['produzione', 'coda'] })
      setRigheSelezionate(new Set())
      toast.success(`${result.commesse_create} commesse create`)
      downloadExcel(result.file_excel_base64, `commesse_${new Date().toISOString().slice(0,10)}.xlsx`)
    },
    onError: (err: unknown) => {
      toast.error(extractApiError(err))
    },
  })

  // ── Handlers ─────────────────────────────────────────────────────────────
  const toggleRiga = (id: string) => {
    setRigheSelezionate(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleGeneraCommesse = () => {
    if (!righeSelezionate.size) return
    generaCommesse.mutate({
      righe: Array.from(righeSelezionate).map(id => ({
        riga_ordine_id: id,
        qty_ciclo_corrente: null,
        qty_scorta: 0,
      })),
      created_by: username ?? 'sistema',
    })
  }

  // ── Render ────────────────────────────────────────────────────────────────
  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError)   return <div className="p-6 text-red-500">Errore nel caricamento dati</div>

  return (
    <div className="space-y-4">

      {/* Header pagina */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Lancio ordini cliente</h1>
          <SyncIndicator tabella="ordini" />
        </div>
        <Button
          onClick={handleGeneraCommesse}
          disabled={!righeSelezionate.size || generaCommesse.isPending}
        >
          {generaCommesse.isPending
            ? 'Generazione...'
            : `Genera commesse (${righeSelezionate.size})`}
        </Button>
      </div>

      {/* Lista righe */}
      {!righe?.length ? (
        <div className="text-muted-foreground py-12 text-center">
          Nessuna riga da processare
        </div>
      ) : (
        <div className="border rounded-lg divide-y">
          {righe.map(riga => (
            <div
              key={riga.riga_ordine_id}
              className="flex items-center gap-4 p-4 hover:bg-muted/30 transition-colors"
            >
              <Checkbox
                checked={righeSelezionate.has(riga.riga_ordine_id)}
                onCheckedChange={() => toggleRiga(riga.riga_ordine_id)}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{riga.codice_articolo}</span>
                  <UrgenzaBadge attiva={riga.flag_urgenza} />
                  {riga.flag_data_scaduta && (
                    <Badge variant="destructive" className="text-xs">Scaduta</Badge>
                  )}
                </div>
                <div className="text-sm text-muted-foreground truncate">
                  {riga.descrizione_articolo}
                </div>
              </div>
              <div className="text-sm text-right">
                <ClienteLabel cliente={riga.cliente} />
                <div className="text-muted-foreground text-xs">{riga.numero_ordine}</div>
              </div>
              <div className="text-sm text-right min-w-[80px]">
                <DataConsegnaLabel
                  data={riga.data_consegna}
                  flagScaduta={riga.flag_data_scaduta}
                />
              </div>
              <div className="text-sm text-right min-w-[100px]">
                <span className="font-medium">{formatQty(riga.qty_da_produrre)}</span>
                <div className="text-muted-foreground text-xs">
                  disp: {formatQty(riga.qty_disponibile)} · prod: {formatQty(riga.qty_in_produzione)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

---

*MRS — Documento interno di sviluppo  |  Marzo 2026*
