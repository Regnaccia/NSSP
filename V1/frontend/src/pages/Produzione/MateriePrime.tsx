/**
 * Configurazione materie prime — lunghezze barre.
 *
 * Lista le materie prime sincronizzate da EasyJob (CAT_ART1=0).
 * L'utente imposta lunghezza_mm per ciascuna.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { officeClient } from '@/api/officeClient'
import { SyncIndicator } from '@/components/SyncIndicator'
import { extractApiError, formatQty } from '@/lib/utils'
import type { MateriaPrimaResponse } from '@/types/api'

export default function MateriePrime() {
  const queryClient = useQueryClient()
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState<Record<string, string>>({})   // id → lunghezza in edit

  const { data: materie, isLoading } = useQuery({
    queryKey: ['materie-prime', q],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (q.trim()) params.q = q.trim().replace(/\./g, 'x')
      const { data } = await officeClient.get<MateriaPrimaResponse[]>('/api/materie-prime', { params })
      return data
    },
  })

  const patch = useMutation({
    mutationFn: async ({ id, lunghezza_mm }: { id: string; lunghezza_mm: number | null }) => {
      await officeClient.patch(`/api/materie-prime/${id}`, { lunghezza_mm })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materie-prime'] })
      toast.success('Lunghezza aggiornata')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  const handleSave = (mp: MateriaPrimaResponse) => {
    const val = editing[mp.id]
    if (val === undefined) return
    const parsed = val === '' ? null : parseInt(val)
    patch.mutate({ id: mp.id, lunghezza_mm: parsed })
    setEditing(prev => { const n = { ...prev }; delete n[mp.id]; return n })
  }

  const handleKeyDown = (e: React.KeyboardEvent, mp: MateriaPrimaResponse) => {
    if (e.key === 'Enter') handleSave(mp)
    if (e.key === 'Escape') setEditing(prev => { const n = { ...prev }; delete n[mp.id]; return n })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Materie prime — lunghezze barre</h1>
          <SyncIndicator tabella="materie_prime" />
        </div>
        <input
          type="text"
          placeholder="Cerca codice... (. = x)"
          value={q}
          onChange={e => setQ(e.target.value.replace(/\./g, 'x'))}
          className="flex h-9 w-48 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
        />
      </div>

      {isLoading ? (
        <div className="text-muted-foreground py-8 text-center">Caricamento...</div>
      ) : !materie?.length ? (
        <div className="text-muted-foreground py-12 text-center border rounded-lg">
          Nessuna materia prima trovata
        </div>
      ) : (
        <div className="border rounded-lg divide-y">
          <div className="grid grid-cols-[1fr_2fr_140px] gap-3 px-4 py-2 bg-muted/50 text-xs font-medium text-muted-foreground">
            <span>Codice</span>
            <span>Descrizione</span>
            <span className="text-right">Lunghezza (mm)</span>
          </div>

          {materie.map(mp => {
            const isEdit = mp.id in editing
            const displayVal = isEdit ? editing[mp.id] : (mp.lunghezza_mm != null ? String(mp.lunghezza_mm) : '')
            return (
              <div
                key={mp.id}
                className="grid grid-cols-[1fr_2fr_140px] gap-3 px-4 py-2.5 items-center hover:bg-muted/20 text-sm"
              >
                <span className="font-mono font-medium">{mp.codice}</span>
                <span className="text-muted-foreground truncate">{mp.descrizione ?? '—'}</span>
                <div className="flex items-center justify-end gap-1">
                  {mp.lunghezza_mm == null && !isEdit && (
                    <span className="text-xs text-amber-600 mr-1">⚠ mancante</span>
                  )}
                  <input
                    type="number"
                    min={1}
                    value={displayVal}
                    placeholder="—"
                    onChange={e => setEditing(prev => ({ ...prev, [mp.id]: e.target.value }))}
                    onBlur={() => isEdit && handleSave(mp)}
                    onKeyDown={e => handleKeyDown(e, mp)}
                    className={`flex h-8 w-24 rounded-md border px-2 text-sm text-right ${
                      isEdit ? 'border-primary ring-1 ring-primary' : 'border-input bg-transparent'
                    }`}
                  />
                  {mp.lunghezza_mm != null && !isEdit && (
                    <span className="text-xs text-muted-foreground">mm</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Modifica la lunghezza direttamente nella cella (Invio o click fuori per salvare).
        Le materie prime vengono sincronizzate da EasyJob (ANAART CAT_ART1=0).
      </p>
    </div>
  )
}
