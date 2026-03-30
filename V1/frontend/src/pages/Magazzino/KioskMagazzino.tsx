import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { CheckCircle, Package, Send } from 'lucide-react'

import { kioskClient } from '@/api/kioskClient'
import { UrgenzaBadge } from '@/components/UrgenzaBadge'
import { DataConsegnaLabel } from '@/components/DataConsegnaLabel'
import { extractApiError, formatQty } from '@/lib/utils'
import { POLLING_INTERVAL } from '@/lib/constants'
import type { OrdineApprontareResponse } from '@/types/api'

export default function KioskMagazzino() {
  const queryClient = useQueryClient()
  const [expandedOrdine, setExpandedOrdine] = useState<string | null>(null)

  const { data: ordini, isLoading, isError } = useQuery({
    queryKey: ['magazzino', 'da-approntare'],
    queryFn: async () => {
      const { data } = await kioskClient.get<OrdineApprontareResponse[]>('/api/magazzino/da-approntare')
      return data
    },
    refetchInterval: POLLING_INTERVAL.KIOSK,
  })

  // ── Mutation: registra consegna articolo ──────────────────────────────────
  const registra = useMutation({
    mutationFn: async ({ commessaId, tipo }: { commessaId: string; tipo: 'cliente' | 'scorta' | 'misto' }) => {
      await kioskClient.post(`/api/magazzino/consegne`, {
        commessa_id: commessaId,
        tipo,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['magazzino', 'da-approntare'] })
      toast.success('Consegna registrata')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: segna ordine pronto ─────────────────────────────────────────
  const segnaPronto = useMutation({
    mutationFn: async (ordineId: string) => {
      await kioskClient.post(`/api/magazzino/ordine-pronto`, {
        ordine_id: ordineId,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['magazzino', 'da-approntare'] })
      toast.success('Ordine segnalato come pronto alla logistica')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-muted-foreground">Caricamento...</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-red-500">Errore di connessione — riprovare</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b p-4 bg-background">
        <div className="flex items-center gap-3">
          <Package className="h-7 w-7 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Magazzino</h1>
            <p className="text-base text-muted-foreground">Ordini da approntare</p>
          </div>
        </div>
      </header>

      <div className="flex-1 p-4 space-y-4">
        {!ordini?.length ? (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <CheckCircle className="h-16 w-16 text-green-400" />
            <p className="text-xl font-medium">Nessun ordine da approntare</p>
          </div>
        ) : (
          ordini.map(o => (
            <OrdineCard
              key={o.ordine_id}
              ordine={o}
              isExpanded={expandedOrdine === o.ordine_id}
              onToggle={() => setExpandedOrdine(
                expandedOrdine === o.ordine_id ? null : o.ordine_id
              )}
              onRegistra={(commessaId, tipo) => registra.mutate({ commessaId, tipo })}
              onSegnaPronto={() => segnaPronto.mutate(o.ordine_id)}
              isPending={registra.isPending || segnaPronto.isPending}
            />
          ))
        )}
      </div>
    </div>
  )
}

function OrdineCard({
  ordine: o,
  isExpanded,
  onToggle,
  onRegistra,
  onSegnaPronto,
  isPending,
}: {
  ordine: OrdineApprontareResponse
  isExpanded: boolean
  onToggle: () => void
  onRegistra: (commessaId: string, tipo: 'cliente' | 'scorta' | 'misto') => void
  onSegnaPronto: () => void
  isPending: boolean
}) {
  const registrate = o.articoli.filter(a => a.gia_registrata).length
  const totali = o.articoli.length
  const tutteOk = o.tutte_registrate

  return (
    <div className={`border-2 rounded-xl overflow-hidden ${tutteOk ? 'border-green-300' : 'border-border'}`}>
      {/* Intestazione ordine */}
      <button
        onClick={onToggle}
        className={`w-full p-4 text-left flex items-center gap-4 ${
          tutteOk ? 'bg-green-50' : 'bg-background'
        } active:bg-muted/50 transition-colors`}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xl font-bold">{o.numero_ordine}</span>
            <UrgenzaBadge attiva={o.flag_urgenza} />
          </div>
          <div className="text-base text-muted-foreground mt-0.5">{o.cliente}</div>
          <div className="flex items-center gap-3 mt-1">
            <DataConsegnaLabel data={o.data_consegna} />
            <span className="text-sm text-muted-foreground">
              {registrate}/{totali} articoli registrati
            </span>
          </div>
        </div>
        <div>
          {tutteOk
            ? <CheckCircle className="h-8 w-8 text-green-500" />
            : <span className="text-3xl font-bold text-muted-foreground/50">{isExpanded ? '▲' : '▼'}</span>
          }
        </div>
      </button>

      {/* Articoli espansi */}
      {isExpanded && (
        <div className="border-t divide-y">
          {o.articoli.map(a => (
            <div key={a.commessa_id} className="p-4 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="text-lg font-medium">{a.codice_articolo}</div>
                {a.descrizione_articolo && (
                  <div className="text-base text-muted-foreground truncate">{a.descrizione_articolo}</div>
                )}
                <div className="text-sm text-muted-foreground mt-1">
                  Tot: {formatQty(a.qty_totale)}
                  {a.qty_prodotta_cliente > 0 && ` · Cliente: ${formatQty(a.qty_prodotta_cliente)}`}
                  {a.qty_prodotta_scorta > 0 && ` · Scorta: ${formatQty(a.qty_prodotta_scorta)}`}
                </div>
              </div>
              {a.gia_registrata ? (
                <CheckCircle className="h-8 w-8 text-green-500 shrink-0" />
              ) : (
                <button
                  onClick={() => {
                    const tipo = a.qty_prodotta_cliente > 0 && a.qty_prodotta_scorta > 0
                      ? 'misto'
                      : a.qty_prodotta_scorta > 0 ? 'scorta' : 'cliente'
                    onRegistra(a.commessa_id, tipo)
                  }}
                  disabled={isPending}
                  className="min-h-[56px] px-5 bg-primary text-primary-foreground rounded-xl text-base font-semibold active:scale-95 transition-transform disabled:opacity-50 shrink-0"
                >
                  Registra
                </button>
              )}
            </div>
          ))}

          {/* Bottone segna pronto */}
          {o.tutte_registrate && (
            <div className="p-4 bg-green-50">
              <button
                onClick={onSegnaPronto}
                disabled={isPending}
                className="w-full min-h-[64px] flex items-center justify-center gap-3 bg-green-600 text-white rounded-xl text-xl font-bold active:scale-95 transition-transform disabled:opacity-50"
              >
                <Send className="h-6 w-6" />
                Segnala ordine pronto alla logistica
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
