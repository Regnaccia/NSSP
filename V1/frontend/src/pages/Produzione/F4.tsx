import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { MessageSquare } from 'lucide-react'

import { useEventi } from '@/hooks/useEventi'
import { officeClient } from '@/api/officeClient'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogClose,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { extractApiError, formatDataOra } from '@/lib/utils'
import type { EventoResponse, FeedbackStato } from '@/types/api'

const LABEL_STATO: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  aperto:         { label: 'Aperta',          variant: 'destructive' },
  in_lavorazione: { label: 'In lavorazione',  variant: 'default' },
  risolto:        { label: 'Risolta',         variant: 'outline' },
  rifiutato:      { label: 'Rifiutata',       variant: 'outline' },
}

export default function ProdF4() {
  const queryClient = useQueryClient()
  const [feedbackEvento, setFeedbackEvento] = useState<EventoResponse | null>(null)

  const { data: urgenze, isLoading, isError } = useEventi({
    tipo: 'urgenza_formale',
    destinatario: 'produzione',
  })

  // ── Mutation: feedback ────────────────────────────────────────────────────
  const daiFeedback = useMutation({
    mutationFn: async ({
      id, stato, dataPrevista, nota,
    }: { id: string; stato: FeedbackStato; dataPrevista: string | null; nota: string }) => {
      const { data } = await officeClient.patch<EventoResponse>(`/api/eventi/${id}/feedback`, {
        stato,
        data_prevista: dataPrevista || null,
        nota: nota || null,
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eventi'] })
      toast.success('Feedback inviato')
      setFeedbackEvento(null)
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError) return <div className="p-6 text-red-500">Errore nel caricamento dati</div>

  const aperte = urgenze?.filter(e => e.stato === 'aperto' || e.stato === 'in_lavorazione') ?? []
  const chiuse = urgenze?.filter(e => e.stato === 'risolto' || e.stato === 'rifiutato') ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Urgenze — Produzione</h1>

      {/* Urgenze aperte */}
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
              <UrgenzaRow
                key={e.id}
                evento={e}
                onFeedback={() => setFeedbackEvento(e)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Urgenze chiuse */}
      {chiuse.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Archivio ({chiuse.length})
          </h2>
          <div className="border rounded-lg divide-y">
            {chiuse.map(e => <UrgenzaRow key={e.id} evento={e} />)}
          </div>
        </section>
      )}

      {/* Dialog feedback */}
      {feedbackEvento && (
        <FeedbackDialog
          evento={feedbackEvento}
          onOpenChange={(open) => { if (!open) setFeedbackEvento(null) }}
          onSubmit={({ stato, dataPrevista, nota }) =>
            daiFeedback.mutate({ id: feedbackEvento.id, stato, dataPrevista, nota })
          }
          isPending={daiFeedback.isPending}
        />
      )}
    </div>
  )
}

function UrgenzaRow({
  evento: e, onFeedback,
}: {
  evento: EventoResponse
  onFeedback?: () => void
}) {
  const cfg = LABEL_STATO[e.stato]
  const chiuso = e.stato === 'risolto' || e.stato === 'rifiutato'
  return (
    <div className="flex items-start gap-4 p-4">
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={cfg.variant}>{cfg.label}</Badge>
          {e.numero_ordine && (
            <span className="text-sm font-medium">{e.numero_ordine}</span>
          )}
          {e.cliente && (
            <span className="text-sm text-muted-foreground">{e.cliente}</span>
          )}
        </div>
        {e.nota && (
          <p className="text-sm">{e.nota}</p>
        )}
        <div className="text-xs text-muted-foreground">
          Da {e.mittente} · {formatDataOra(e.created_at)}
        </div>
        {e.feedback_stato && (
          <div className="text-xs text-muted-foreground border-l-2 pl-2 mt-1">
            Feedback: {e.feedback_stato === 'accettata' ? 'Accettata' : 'Non fattibile'}
            {e.feedback_data_prevista && ` · prevista per ${e.feedback_data_prevista}`}
            {e.feedback_nota && ` · ${e.feedback_nota}`}
          </div>
        )}
      </div>
      {!chiuso && onFeedback && (
        <Button variant="outline" size="sm" onClick={onFeedback}>
          <MessageSquare className="h-4 w-4" />
          Feedback
        </Button>
      )}
    </div>
  )
}

function FeedbackDialog({
  evento, onOpenChange, onSubmit, isPending,
}: {
  evento: EventoResponse
  onOpenChange: (v: boolean) => void
  onSubmit: (v: { stato: FeedbackStato; dataPrevista: string | null; nota: string }) => void
  isPending: boolean
}) {
  const [stato, setStato] = useState<FeedbackStato>('accettata')
  const [dataPrevista, setDataPrevista] = useState('')
  const [nota, setNota] = useState('')

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Feedback urgenza {evento.numero_ordine ?? ''}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Risposta</Label>
            <Select value={stato} onValueChange={v => setStato(v as FeedbackStato)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="accettata">Accettata — possiamo consegnare</SelectItem>
                <SelectItem value="non_fattibile">Non fattibile</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {stato === 'accettata' && (
            <div className="space-y-2">
              <Label>Data prevista consegna</Label>
              <Input
                type="date"
                value={dataPrevista}
                onChange={e => setDataPrevista(e.target.value)}
              />
            </div>
          )}
          <div className="space-y-2">
            <Label>Note (opzionale)</Label>
            <Textarea
              value={nota}
              onChange={e => setNota(e.target.value)}
              placeholder="Motivazione o informazioni aggiuntive..."
            />
          </div>
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Annulla</Button>
          </DialogClose>
          <Button
            onClick={() => onSubmit({ stato, dataPrevista: dataPrevista || null, nota })}
            disabled={isPending}
          >
            {isPending ? 'Invio...' : 'Invia feedback'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
