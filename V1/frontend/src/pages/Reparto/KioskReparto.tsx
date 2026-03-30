import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ArrowLeft, Play, Pause, RotateCcw, CheckCircle, AlertCircle } from 'lucide-react'

import { kioskClient } from '@/api/kioskClient'
import { CommessaStatusBadge } from '@/components/CommessaStatusBadge'
import { UrgenzaBadge } from '@/components/UrgenzaBadge'
import { extractApiError, formatQty } from '@/lib/utils'
import { POLLING_INTERVAL } from '@/lib/constants'
import type { CommessaResponse, MacchinaResponse } from '@/types/api'

export default function KioskReparto() {
  const { macchinaId } = useParams<{ macchinaId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [notaSospensione, setNotaSospensione] = useState('')
  const [showNotaInput, setShowNotaInput] = useState(false)
  const [commessaInAzione, setCommessaInAzione] = useState<string | null>(null)

  // ── Macchina info ─────────────────────────────────────────────────────────
  const { data: macchina } = useQuery({
    queryKey: ['reparto', 'macchina', macchinaId],
    queryFn: async () => {
      const { data } = await kioskClient.get<MacchinaResponse>(`/api/reparto/macchine/${macchinaId}`)
      return data
    },
    enabled: Boolean(macchinaId),
  })

  // ── Coda commesse ─────────────────────────────────────────────────────────
  const { data: coda, isLoading } = useQuery({
    queryKey: ['reparto', 'coda', macchinaId],
    queryFn: async () => {
      const { data } = await kioskClient.get<CommessaResponse[]>(
        `/api/reparto/macchine/${macchinaId}/coda`
      )
      return data
    },
    refetchInterval: POLLING_INTERVAL.KIOSK,
    enabled: Boolean(macchinaId),
  })

  const invalidateCoda = () => {
    queryClient.invalidateQueries({ queryKey: ['reparto', 'coda', macchinaId] })
  }

  // ── Mutation: avvia ───────────────────────────────────────────────────────
  const avvia = useMutation({
    mutationFn: async (id: string) => {
      const { data } = await kioskClient.post<CommessaResponse>(`/api/reparto/commesse/${id}/avvia`)
      return data
    },
    onSuccess: () => { invalidateCoda(); toast.success('Commessa avviata') },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: sospendi ────────────────────────────────────────────────────
  const sospendi = useMutation({
    mutationFn: async ({ id, nota }: { id: string; nota?: string }) => {
      const { data } = await kioskClient.post<CommessaResponse>(
        `/api/reparto/commesse/${id}/sospendi`,
        { nota: nota || null }
      )
      return data
    },
    onSuccess: () => {
      invalidateCoda()
      toast.success('Commessa sospesa')
      setShowNotaInput(false)
      setNotaSospensione('')
      setCommessaInAzione(null)
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: riprendi ────────────────────────────────────────────────────
  const riprendi = useMutation({
    mutationFn: async (id: string) => {
      const { data } = await kioskClient.post<CommessaResponse>(`/api/reparto/commesse/${id}/riprendi`)
      return data
    },
    onSuccess: () => { invalidateCoda(); toast.success('Commessa ripresa') },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: completa ────────────────────────────────────────────────────
  const completa = useMutation({
    mutationFn: async (id: string) => {
      const { data } = await kioskClient.post<CommessaResponse>(`/api/reparto/commesse/${id}/completa`)
      return data
    },
    onSuccess: () => { invalidateCoda(); toast.success('Commessa completata') },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: aggiorna qty ────────────────────────────────────────────────
  const aggiornaQty = useMutation({
    mutationFn: async ({ id, qtyProdottaCliente, qtyProdottaScorta }: {
      id: string
      qtyProdottaCliente: number
      qtyProdottaScorta: number
    }) => {
      const { data } = await kioskClient.post<CommessaResponse>(
        `/api/reparto/commesse/${id}/aggiorna-qty`,
        { qty_prodotta_cliente: qtyProdottaCliente, qty_prodotta_scorta: qtyProdottaScorta }
      )
      return data
    },
    onSuccess: () => { invalidateCoda(); toast.success('Quantità aggiornata') },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-muted-foreground">Caricamento coda...</p>
      </div>
    )
  }

  const commessaAttiva = coda?.find(c => c.stato === 'in_produzione')
  const codaInAttesa = coda?.filter(c => c.stato === 'in_coda') ?? []
  const sospese = coda?.filter(c => c.stato === 'sospesa') ?? []

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b p-4 flex items-center gap-4 bg-background">
        <button
          onClick={() => navigate('/reparto')}
          className="p-2 rounded-lg hover:bg-muted transition-colors"
        >
          <ArrowLeft className="h-6 w-6" />
        </button>
        <div>
          <h1 className="text-2xl font-bold">{macchina?.codice ?? 'Macchina'}</h1>
          <p className="text-base text-muted-foreground">{macchina?.nome}</p>
        </div>
      </header>

      <div className="flex-1 p-4 space-y-6">
        {/* Commessa attiva */}
        {commessaAttiva ? (
          <section>
            <h2 className="text-base font-semibold text-muted-foreground uppercase tracking-wide mb-3">
              In lavorazione
            </h2>
            <CommessaCard
              commessa={commessaAttiva}
              onSospendi={() => {
                setCommessaInAzione(commessaAttiva.id)
                setShowNotaInput(true)
              }}
              onCompleta={() => completa.mutate(commessaAttiva.id)}
              onAggiornaQty={(qc, qs) => aggiornaQty.mutate({
                id: commessaAttiva.id,
                qtyProdottaCliente: qc,
                qtyProdottaScorta: qs,
              })}
              isPending={sospendi.isPending || completa.isPending || aggiornaQty.isPending}
              isAttiva
            />

            {/* Nota sospensione */}
            {showNotaInput && commessaInAzione === commessaAttiva.id && (
              <div className="mt-3 p-4 border rounded-xl bg-yellow-50 space-y-3">
                <p className="text-base font-medium">Motivo sospensione (opzionale):</p>
                <textarea
                  value={notaSospensione}
                  onChange={e => setNotaSospensione(e.target.value)}
                  className="w-full border rounded-lg p-3 text-base min-h-[80px] bg-white"
                  placeholder="es. attesa materiale, guasto attrezzo..."
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => sospendi.mutate({ id: commessaAttiva.id, nota: notaSospensione })}
                    className="flex-1 bg-yellow-500 text-white rounded-xl py-4 text-lg font-semibold active:scale-95 transition-transform"
                  >
                    Conferma sospensione
                  </button>
                  <button
                    onClick={() => { setShowNotaInput(false); setNotaSospensione('') }}
                    className="px-6 border rounded-xl py-4 text-lg active:scale-95 transition-transform"
                  >
                    Annulla
                  </button>
                </div>
              </div>
            )}
          </section>
        ) : (
          <div className="flex items-center gap-3 p-4 border rounded-xl bg-muted/30">
            <AlertCircle className="h-6 w-6 text-muted-foreground" />
            <p className="text-lg text-muted-foreground">Nessuna commessa in lavorazione</p>
          </div>
        )}

        {/* Sospese */}
        {sospese.length > 0 && (
          <section>
            <h2 className="text-base font-semibold text-muted-foreground uppercase tracking-wide mb-3">
              Sospese ({sospese.length})
            </h2>
            <div className="space-y-2">
              {sospese.map(c => (
                <CommessaCard
                  key={c.id}
                  commessa={c}
                  onRiprendi={() => riprendi.mutate(c.id)}
                  isPending={riprendi.isPending}
                />
              ))}
            </div>
          </section>
        )}

        {/* Coda */}
        {codaInAttesa.length > 0 && (
          <section>
            <h2 className="text-base font-semibold text-muted-foreground uppercase tracking-wide mb-3">
              Prossime ({codaInAttesa.length})
            </h2>
            <div className="space-y-2">
              {codaInAttesa.map(c => (
                <CommessaCard
                  key={c.id}
                  commessa={c}
                  onAvvia={!commessaAttiva ? () => avvia.mutate(c.id) : undefined}
                  isPending={avvia.isPending}
                />
              ))}
            </div>
          </section>
        )}

        {!commessaAttiva && codaInAttesa.length === 0 && sospese.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
            <CheckCircle className="h-16 w-16 text-green-400" />
            <p className="text-xl font-medium">Coda vuota — tutto completato!</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Card commessa (touch-first) ──────────────────────────────────────────────

function CommessaCard({
  commessa: c,
  isAttiva = false,
  onAvvia,
  onSospendi,
  onRiprendi,
  onCompleta,
  onAggiornaQty,
  isPending,
}: {
  commessa: CommessaResponse
  isAttiva?: boolean
  onAvvia?: () => void
  onSospendi?: () => void
  onRiprendi?: () => void
  onCompleta?: () => void
  onAggiornaQty?: (qtyCliente: number, qtyScorta: number) => void
  isPending?: boolean
}) {
  const [showQtyInput, setShowQtyInput] = useState(false)
  const [qtyCliente, setQtyCliente] = useState(c.qty_prodotta_cliente.toString())
  const [qtyScorta, setQtyScorta] = useState(c.qty_prodotta_scorta.toString())
  const urgente = c.priorita_suggerita === 1

  return (
    <div className={`border-2 rounded-xl p-4 ${isAttiva ? 'border-blue-400 bg-blue-50' : 'border-border bg-background'}`}>
      {/* Info commessa */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <CommessaStatusBadge stato={c.stato} />
            {urgente && <UrgenzaBadge attiva />}
            {c.posizione_coda != null && (
              <span className="text-sm text-muted-foreground">#{c.posizione_coda}</span>
            )}
          </div>
          <div className="text-2xl font-bold mt-2">{c.codice_articolo}</div>
          {c.descrizione_articolo && (
            <div className="text-base text-muted-foreground mt-0.5 truncate">{c.descrizione_articolo}</div>
          )}
          {c.numero_ordine && (
            <div className="text-sm text-muted-foreground">{c.numero_ordine}</div>
          )}
        </div>
        <div className="text-right shrink-0">
          <div className="text-3xl font-bold">{formatQty(c.qty_residua)}</div>
          <div className="text-base text-muted-foreground">/ {formatQty(c.qty_totale)}</div>
        </div>
      </div>

      {/* Aggiorna quantità */}
      {isAttiva && onAggiornaQty && (
        <div className="mb-4">
          {!showQtyInput ? (
            <button
              onClick={() => setShowQtyInput(true)}
              className="text-sm text-blue-600 underline"
            >
              Aggiorna quantità prodotta
            </button>
          ) : (
            <div className="space-y-2">
              <div className="flex gap-3">
                {c.qty_cliente > 0 && (
                  <div>
                    <label className="text-sm font-medium">Qt cliente</label>
                    <input
                      type="number"
                      min="0"
                      value={qtyCliente}
                      onChange={e => setQtyCliente(e.target.value)}
                      className="border rounded-lg p-2 text-lg w-28 block mt-1"
                    />
                  </div>
                )}
                {c.qty_scorta > 0 && (
                  <div>
                    <label className="text-sm font-medium">Qt scorta</label>
                    <input
                      type="number"
                      min="0"
                      value={qtyScorta}
                      onChange={e => setQtyScorta(e.target.value)}
                      className="border rounded-lg p-2 text-lg w-28 block mt-1"
                    />
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    onAggiornaQty(parseInt(qtyCliente) || 0, parseInt(qtyScorta) || 0)
                    setShowQtyInput(false)
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm active:scale-95"
                >
                  Salva
                </button>
                <button onClick={() => setShowQtyInput(false)} className="px-4 py-2 border rounded-lg text-sm">
                  Annulla
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sospesa nota */}
      {c.stato === 'sospesa' && c.sospesa_nota && (
        <div className="mb-3 text-sm text-muted-foreground border-l-2 pl-2">{c.sospesa_nota}</div>
      )}

      {/* Azioni — bottoni grandi touch-friendly */}
      <div className="flex gap-3 flex-wrap">
        {onAvvia && (
          <button
            onClick={onAvvia}
            disabled={isPending}
            className="flex-1 min-h-[56px] flex items-center justify-center gap-2 bg-green-600 text-white rounded-xl text-lg font-semibold active:scale-95 transition-transform disabled:opacity-50"
          >
            <Play className="h-5 w-5" /> Avvia
          </button>
        )}
        {onRiprendi && (
          <button
            onClick={onRiprendi}
            disabled={isPending}
            className="flex-1 min-h-[56px] flex items-center justify-center gap-2 bg-blue-600 text-white rounded-xl text-lg font-semibold active:scale-95 transition-transform disabled:opacity-50"
          >
            <RotateCcw className="h-5 w-5" /> Riprendi
          </button>
        )}
        {onSospendi && isAttiva && (
          <button
            onClick={onSospendi}
            disabled={isPending}
            className="flex-1 min-h-[56px] flex items-center justify-center gap-2 bg-yellow-500 text-white rounded-xl text-lg font-semibold active:scale-95 transition-transform disabled:opacity-50"
          >
            <Pause className="h-5 w-5" /> Sospendi
          </button>
        )}
        {onCompleta && isAttiva && (
          <button
            onClick={onCompleta}
            disabled={isPending}
            className="flex-1 min-h-[56px] flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-xl text-lg font-semibold active:scale-95 transition-transform disabled:opacity-50"
          >
            <CheckCircle className="h-5 w-5" /> Completata
          </button>
        )}
      </div>
    </div>
  )
}
