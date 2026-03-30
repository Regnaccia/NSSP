import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { officeClient } from '@/api/officeClient'
import { useAuthStore } from '@/store/authStore'
import { SyncIndicator } from '@/components/SyncIndicator'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { extractApiError, downloadExcel, formatQty, formatData } from '@/lib/utils'
import { POLLING_INTERVAL } from '@/lib/constants'
import type { ArticoloF1bResponse, GeneraCommesseResponse } from '@/types/api'
import { RefreshCw } from 'lucide-react'

export default function F1b() {
  const { username } = useAuthStore()
  const queryClient = useQueryClient()
  const [selezionati, setSelezionati] = useState<Set<string>>(new Set())

  // ── Query articoli F1b ────────────────────────────────────────────────────
  const { data: articoli, isLoading, isError } = useQuery({
    queryKey: ['produzione', 'f1b'],
    queryFn: async () => {
      const { data } = await officeClient.get<ArticoloF1bResponse[]>('/api/produzione/f1b')
      return data
    },
    refetchInterval: POLLING_INTERVAL.OFFICE,
  })

  // ── Mutation: genera commesse scorta ─────────────────────────────────────
  const generaCommesse = useMutation({
    mutationFn: async (righe: ArticoloF1bResponse[]) => {
      const { data } = await officeClient.post<GeneraCommesseResponse>(
        '/api/produzione/genera-commesse',
        {
          righe: righe.map(a => ({
            riga_ordine_id: null,
            articolo_id: a.articolo_id,
            qty_ciclo_corrente: null,
            qty_scorta: a.qty_da_produrre_scorta,
          })),
          created_by: username ?? 'sistema',
        }
      )
      return data
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['produzione', 'f1b'] })
      queryClient.invalidateQueries({ queryKey: ['produzione', 'coda'] })
      setSelezionati(new Set())
      toast.success(`${result.commesse_create} commesse create`)
      downloadExcel(
        result.file_excel_base64,
        `scorte_${new Date().toISOString().slice(0, 10)}.xlsx`
      )
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: ricalcola scorte ────────────────────────────────────────────
  const ricalcola = useMutation({
    mutationFn: async () => {
      const { data } = await officeClient.post<{ aggiornati: number }>(
        '/api/produzione/ricalcola-scorte', {}
      )
      return data
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['produzione', 'f1b'] })
      toast.success(`Scorte ricalcolate: ${result.aggiornati} articoli aggiornati`)
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  const toggleArticolo = (id: string) => {
    setSelezionati(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleGeneraCommesse = () => {
    if (!articoli || !selezionati.size) return
    const righe = articoli.filter(a => selezionati.has(a.articolo_id))
    generaCommesse.mutate(righe)
  }

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError) return <div className="p-6 text-red-500">Errore nel caricamento dati</div>

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Lancio scorte</h1>
          <SyncIndicator tabella="articoli" />
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => ricalcola.mutate()}
            disabled={ricalcola.isPending}
          >
            <RefreshCw className={`h-4 w-4 ${ricalcola.isPending ? 'animate-spin' : ''}`} />
            Ricalcola scorte
          </Button>
          <Button
            onClick={handleGeneraCommesse}
            disabled={!selezionati.size || generaCommesse.isPending}
          >
            {generaCommesse.isPending
              ? 'Generazione...'
              : `Genera commesse (${selezionati.size})`}
          </Button>
        </div>
      </div>

      {/* Lista articoli */}
      {!articoli?.length ? (
        <div className="text-muted-foreground py-12 text-center border rounded-lg">
          Nessun articolo da ricostituire
        </div>
      ) : (
        <div className="border rounded-lg divide-y">
          {/* Header */}
          <div className="flex items-center gap-4 px-4 py-2 bg-muted/50 text-xs font-medium text-muted-foreground">
            <div className="w-4" />
            <span className="w-32">Codice</span>
            <span className="flex-1">Descrizione</span>
            <span className="min-w-[80px] text-right">Disponibile</span>
            <span className="min-w-[80px] text-right">Target</span>
            <span className="min-w-[80px] text-right">Da produrre</span>
          </div>

          {articoli.map(a => {
            const critico = a.qty_disponibile_futura <= 0
            return (
              <div
                key={a.articolo_id}
                className="flex items-center gap-4 p-4 hover:bg-muted/30 transition-colors cursor-pointer"
                onClick={() => toggleArticolo(a.articolo_id)}
              >
                <Checkbox
                  checked={selezionati.has(a.articolo_id)}
                  onCheckedChange={() => toggleArticolo(a.articolo_id)}
                  onClick={e => e.stopPropagation()}
                />
                <span className="w-32 font-mono text-sm font-medium">{a.codice}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm truncate">{a.descrizione ?? '—'}</div>
                  <div className="flex gap-2 mt-0.5">
                    <Badge variant="secondary" className="text-xs">{a.tipo_produzione}</Badge>
                    {!a.scorta_calcolata_at && (
                      <Badge variant="outline" className="text-xs text-yellow-600">
                        Storico insufficiente
                      </Badge>
                    )}
                    {a.scorta_calcolata_at && (
                      <span className="text-xs text-muted-foreground">
                        Calc. {formatData(a.scorta_calcolata_at)}
                      </span>
                    )}
                  </div>
                </div>
                <div className={`text-sm text-right min-w-[80px] ${critico ? 'text-red-600 font-semibold' : ''}`}>
                  {formatQty(a.qty_disponibile_futura)}
                </div>
                <div className="text-sm text-right min-w-[80px] text-muted-foreground">
                  {formatQty(a.target_scorta)}
                </div>
                <div className="text-sm text-right min-w-[80px] font-medium">
                  {formatQty(a.qty_da_produrre_scorta)}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
