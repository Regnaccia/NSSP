import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, CheckCircle, XCircle } from 'lucide-react'

import { useEventi } from '@/hooks/useEventi'
import { officeClient } from '@/api/officeClient'
import { useAuthStore } from '@/store/authStore'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogClose,
} from '@/components/ui/dialog'
import { extractApiError, formatDataOra } from '@/lib/utils'
import type { EventoResponse } from '@/types/api'

const LABEL_STATO: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  aperto:         { label: 'Aperta',         variant: 'destructive' },
  in_lavorazione: { label: 'In lavorazione', variant: 'default' },
  risolto:        { label: 'Risolta',        variant: 'outline' },
  rifiutato:      { label: 'Rifiutata',      variant: 'outline' },
}

export default function LogF4() {
  const queryClient = useQueryClient()
  const { username } = useAuthStore()
  const [openCrea, setOpenCrea] = useState(false)

  const { data: urgenze, isLoading, isError } = useEventi({
    tipo: 'urgenza_formale',
    destinatario: 'produzione',
  })

  // ── Mutation: crea urgenza ────────────────────────────────────────────────
  const creaUrgenza = useMutation({
    mutationFn: async ({ ordineId, nota }: { ordineId: string; nota: string }) => {
      const { data } = await officeClient.post<EventoResponse>('/api/eventi/urgenza', {
        ref_ordine_id: ordineId,
        nota: nota || null,
        mittente: username ?? 'logistica',
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eventi'] })
      toast.success('Urgenza segnalata al reparto produzione')
      setOpenCrea(false)
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: risolvi ─────────────────────────────────────────────────────
  const risolvi = useMutation({
    mutationFn: async (id: string) => {
      await officeClient.post(`/api/eventi/${id}/risolvi`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eventi'] })
      toast.success('Urgenza risolta')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: rifiuta ─────────────────────────────────────────────────────
  const rifiuta = useMutation({
    mutationFn: async (id: string) => {
      await officeClient.post(`/api/eventi/${id}/rifiuta`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eventi'] })
      toast.success('Urgenza rifiutata')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError) return <div className="p-6 text-red-500">Errore nel caricamento dati</div>

  const aperte = urgenze?.filter(e => e.stato === 'aperto' || e.stato === 'in_lavorazione') ?? []
  const chiuse = urgenze?.filter(e => e.stato === 'risolto' || e.stato === 'rifiutato') ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Urgenze — Logistica</h1>
        <Button size="sm" onClick={() => setOpenCrea(true)}>
          <Plus className="h-4 w-4" />
          Segnala urgenza
        </Button>
      </div>

      {/* Aperte */}
      <section>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
          Da gestire ({aperte.length})
        </h2>
        {aperte.length === 0 ? (
          <div className="text-muted-foreground py-8 text-center border rounded-lg">
            Nessuna urgenza aperta
          </div>
        ) : (
          <div className="border rounded-lg divide-y">
            {aperte.map(e => (
              <EventoRow
                key={e.id}
                evento={e}
                onRisolvi={() => risolvi.mutate(e.id)}
                onRifiuta={() => rifiuta.mutate(e.id)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Archivio */}
      {chiuse.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Archivio ({chiuse.length})
          </h2>
          <div className="border rounded-lg divide-y">
            {chiuse.map(e => <EventoRow key={e.id} evento={e} />)}
          </div>
        </section>
      )}

      {/* Dialog crea urgenza */}
      {openCrea && (
        <CreaUrgenzaDialog
          onOpenChange={setOpenCrea}
          onSubmit={({ ordineId, nota }) => creaUrgenza.mutate({ ordineId, nota })}
          isPending={creaUrgenza.isPending}
        />
      )}
    </div>
  )
}

function EventoRow({ evento: e, onRisolvi, onRifiuta }: {
  evento: EventoResponse
  onRisolvi?: () => void
  onRifiuta?: () => void
}) {
  const cfg = LABEL_STATO[e.stato]
  const chiuso = e.stato === 'risolto' || e.stato === 'rifiutato'
  return (
    <div className="flex items-start gap-4 p-4">
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={cfg.variant}>{cfg.label}</Badge>
          {e.numero_ordine && <span className="font-medium text-sm">{e.numero_ordine}</span>}
          {e.cliente && <span className="text-sm text-muted-foreground">{e.cliente}</span>}
        </div>
        {e.nota && <p className="text-sm">{e.nota}</p>}
        <div className="text-xs text-muted-foreground">
          Da {e.mittente} · {formatDataOra(e.created_at)}
        </div>
        {e.feedback_stato && (
          <div className="text-xs border-l-2 pl-2">
            Risposta produzione: {e.feedback_stato === 'accettata' ? 'Accettata' : 'Non fattibile'}
            {e.feedback_data_prevista && ` · ${e.feedback_data_prevista}`}
            {e.feedback_nota && ` · ${e.feedback_nota}`}
          </div>
        )}
      </div>
      {!chiuso && (
        <div className="flex gap-1">
          {onRisolvi && (
            <Button variant="ghost" size="icon" title="Segna come risolta" onClick={onRisolvi}>
              <CheckCircle className="h-4 w-4 text-green-600" />
            </Button>
          )}
          {onRifiuta && (
            <Button variant="ghost" size="icon" title="Rifiuta" onClick={onRifiuta}>
              <XCircle className="h-4 w-4 text-red-600" />
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

function CreaUrgenzaDialog({ onOpenChange, onSubmit, isPending }: {
  onOpenChange: (v: boolean) => void
  onSubmit: (v: { ordineId: string; nota: string }) => void
  isPending: boolean
}) {
  const [ordineId, setOrdineId] = useState('')
  const [nota, setNota] = useState('')

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Segnala urgenza</DialogTitle></DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Ordine ID</Label>
            <Input value={ordineId} onChange={e => setOrdineId(e.target.value)} placeholder="UUID ordine" />
          </div>
          <div className="space-y-2">
            <Label>Nota (opzionale)</Label>
            <Textarea
              value={nota}
              onChange={e => setNota(e.target.value)}
              placeholder="Descrivi il motivo dell'urgenza..."
            />
          </div>
        </div>
        <DialogFooter>
          <DialogClose asChild><Button variant="outline">Annulla</Button></DialogClose>
          <Button onClick={() => onSubmit({ ordineId, nota })} disabled={isPending || !ordineId}>
            {isPending ? 'Invio...' : 'Segnala urgenza'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
