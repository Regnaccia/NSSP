import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { GripVertical, Wrench } from 'lucide-react'

import { useCodaProduzione } from '@/hooks/useCommesse'
import { officeClient } from '@/api/officeClient'
import { CommessaStatusBadge } from '@/components/CommessaStatusBadge'
import { UrgenzaBadge } from '@/components/UrgenzaBadge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { extractApiError, formatQty } from '@/lib/utils'
import type { CommessaResponse } from '@/types/api'

export default function F2() {
  const queryClient = useQueryClient()
  const { data: commesse, isLoading, isError } = useCodaProduzione()
  const [macchinaFilter, setMacchinaFilter] = useState<string>('tutte')

  // ── Mutation: assegna macchina ────────────────────────────────────────────
  const assegnaMacchina = useMutation({
    mutationFn: async ({ commessaId, macchinaId }: { commessaId: string; macchinaId: string }) => {
      const { data } = await officeClient.post<CommessaResponse>(
        `/api/produzione/coda/${commessaId}/assegna-macchina`,
        { macchina_id: macchinaId }
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produzione', 'coda'] })
      toast.success('Macchina assegnata')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: riordina coda ───────────────────────────────────────────────
  const riordinaCoda = useMutation({
    mutationFn: async (orderedIds: string[]) => {
      await officeClient.post('/api/produzione/coda/riordina', { ids: orderedIds })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produzione', 'coda'] })
      toast.success('Coda riordinata')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError) return <div className="p-6 text-red-500">Errore nel caricamento dati</div>

  // Macchine univoche presenti in coda
  const macchine = Array.from(
    new Set((commesse ?? []).filter(c => c.macchina_codice).map(c => c.macchina_codice!))
  )

  const filtered = macchinaFilter === 'tutte'
    ? (commesse ?? [])
    : (commesse ?? []).filter(c => c.macchina_codice === macchinaFilter)

  const inCoda = filtered.filter(c => c.stato === 'in_coda')
  const inProduzione = filtered.filter(c => c.stato === 'in_produzione')

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Schedulazione</h1>
        <div className="flex items-center gap-2">
          {macchine.length > 0 && (
            <Select value={macchinaFilter} onValueChange={setMacchinaFilter}>
              <SelectTrigger className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tutte">Tutte le macchine</SelectItem>
                {macchine.map(m => (
                  <SelectItem key={m} value={m!}>{m}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </div>

      {/* In produzione */}
      {inProduzione.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            In produzione ({inProduzione.length})
          </h2>
          <div className="border rounded-lg divide-y">
            {inProduzione.map(c => (
              <CommessaRow key={c.id} commessa={c} />
            ))}
          </div>
        </section>
      )}

      {/* Coda */}
      <section>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
          In coda ({inCoda.length})
        </h2>
        {inCoda.length === 0 ? (
          <div className="text-muted-foreground py-8 text-center border rounded-lg">
            Coda vuota
          </div>
        ) : (
          <div className="border rounded-lg divide-y">
            {inCoda.map(c => (
              <CommessaRow key={c.id} commessa={c} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function CommessaRow({ commessa: c }: { commessa: CommessaResponse }) {
  const urgente = c.priorita_suggerita === 1
  return (
    <div className="flex items-center gap-3 p-3 hover:bg-muted/30 transition-colors">
      <GripVertical className="h-4 w-4 text-muted-foreground/50 cursor-grab" />
      <div className="w-6 text-center text-xs text-muted-foreground font-mono">
        {c.posizione_coda ?? '—'}
      </div>
      <CommessaStatusBadge stato={c.stato} />
      {urgente && <UrgenzaBadge attiva />}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm">{c.codice_articolo}</div>
        <div className="text-xs text-muted-foreground truncate">
          {c.descrizione_articolo ?? '—'}
          {c.numero_ordine && ` · ${c.numero_ordine}`}
        </div>
      </div>
      <div className="text-sm text-right">
        <div className="font-medium">{formatQty(c.qty_residua)}</div>
        <div className="text-xs text-muted-foreground">/ {formatQty(c.qty_totale)}</div>
      </div>
      {c.macchina_codice && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground border rounded px-2 py-1">
          <Wrench className="h-3 w-3" />
          {c.macchina_codice}
        </div>
      )}
    </div>
  )
}
