import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { officeClient } from '@/api/officeClient'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { extractApiError, formatQty } from '@/lib/utils'
import type { ArticoloResponse } from '@/types/api'
import { Settings2 } from 'lucide-react'

type Famiglia = 'standard' | 'speciali' | 'barre'

const FAMIGLIE: { value: Famiglia; label: string }[] = [
  { value: 'standard', label: 'Standard' },
  { value: 'speciali', label: 'Speciali' },
  { value: 'barre',    label: 'Barre' },
]

const TIPO_PRODUZIONE_OPTIONS = ['PEZZO', 'BARRA', 'FASCI']

function EditArticoloDialog({
  articolo,
  onClose,
}: {
  articolo: ArticoloResponse
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [capienza, setCapienza] = useState(String(articolo.capienza ?? ''))
  const [mesiScorta, setMesiScorta] = useState(String(articolo.mesi_scorta))
  const [tipoProduzione, setTipoProduzione] = useState(articolo.tipo_produzione)
  const [multipliTaglio, setMultipliTaglio] = useState(String(articolo.multipli_taglio ?? ''))

  const save = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        tipo_produzione: tipoProduzione,
        mesi_scorta: parseInt(mesiScorta) || articolo.mesi_scorta,
      }
      if (capienza !== '') body.capienza = parseInt(capienza) || null
      if (multipliTaglio !== '') body.multipli_taglio = parseInt(multipliTaglio) || null
      await officeClient.patch(`/api/articoli/${articolo.id}`, body)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articoli'] })
      toast.success('Articolo aggiornato')
      onClose()
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="font-mono text-base">{articolo.codice}</DialogTitle>
          <p className="text-sm text-muted-foreground">{articolo.descrizione}</p>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <label className="text-sm font-medium">Tipo produzione</label>
            <Select value={tipoProduzione} onValueChange={setTipoProduzione}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIPO_PRODUZIONE_OPTIONS.map(t => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">Mesi di scorta</label>
            <input
              type="number"
              min={1}
              max={12}
              value={mesiScorta}
              onChange={e => setMesiScorta(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">Capienza magazzino</label>
            <p className="text-xs text-muted-foreground">
              Max pezzi fisicamente stoccabili. Lascia vuoto = illimitata.
            </p>
            <input
              type="number"
              min={0}
              value={capienza}
              onChange={e => setCapienza(e.target.value)}
              placeholder="—"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">Multipli di taglio</label>
            <input
              type="number"
              min={1}
              value={multipliTaglio}
              onChange={e => setMultipliTaglio(e.target.value)}
              placeholder="—"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1 text-sm border-t text-muted-foreground">
            <div>
              <div className="font-medium text-foreground">Giacenza attuale</div>
              <div>{formatQty(articolo.giacenza_attuale)}</div>
            </div>
            <div>
              <div className="font-medium text-foreground">Scorta mensile calc.</div>
              <div>
                {articolo.storico_sufficiente
                  ? formatQty(articolo.scorta_mensile)
                  : <span className="text-yellow-600">Storico insufficiente</span>}
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Annulla</Button>
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? 'Salvataggio...' : 'Salva'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default function Articoli() {
  const [famiglia, setFamiglia] = useState<Famiglia>('standard')
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState<ArticoloResponse | null>(null)

  const { data: articoli, isLoading } = useQuery({
    queryKey: ['articoli', famiglia, q],
    queryFn: async () => {
      const params: Record<string, string> = { famiglia }
      if (q.trim()) params.q = q.trim()
      const { data } = await officeClient.get<ArticoloResponse[]>('/api/articoli', { params })
      return data
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">Parametri articoli</h1>
        <input
          type="text"
          placeholder="Cerca codice..."
          value={q}
          onChange={e => setQ(e.target.value)}
          className="flex h-9 w-48 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
        />
      </div>

      {/* Tab famiglia */}
      <div className="flex gap-1 border-b">
        {FAMIGLIE.map(f => (
          <button
            key={f.value}
            onClick={() => setFamiglia(f.value)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              famiglia === f.value
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-muted-foreground py-8 text-center">Caricamento...</div>
      ) : !articoli?.length ? (
        <div className="text-muted-foreground py-12 text-center border rounded-lg">
          Nessun articolo trovato
        </div>
      ) : (
        <div className="border rounded-lg divide-y">
          {/* Header */}
          <div className="grid grid-cols-[1fr_2fr_80px_80px_80px_80px_40px] gap-3 px-4 py-2 bg-muted/50 text-xs font-medium text-muted-foreground">
            <span>Codice</span>
            <span>Descrizione</span>
            <span className="text-right">Giacenza</span>
            <span className="text-right">Capienza</span>
            <span className="text-right">Mesi scorta</span>
            <span>Tipo prod.</span>
            <span />
          </div>

          {articoli.map(art => (
            <div
              key={art.id}
              className="grid grid-cols-[1fr_2fr_80px_80px_80px_80px_40px] gap-3 px-4 py-3 items-center hover:bg-muted/20 text-sm"
            >
              <span className="font-mono font-medium">{art.codice}</span>
              <span className="text-muted-foreground truncate">{art.descrizione ?? '—'}</span>
              <span className="text-right">{formatQty(art.giacenza_attuale)}</span>
              <span className="text-right text-muted-foreground">
                {art.capienza != null ? formatQty(art.capienza) : <span className="text-xs">—</span>}
              </span>
              <span className="text-right">{art.mesi_scorta}</span>
              <Badge variant="secondary" className="text-xs w-fit">{art.tipo_produzione}</Badge>
              <button
                onClick={() => setEditing(art)}
                className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
              >
                <Settings2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {editing && (
        <EditArticoloDialog articolo={editing} onClose={() => setEditing(null)} />
      )}
    </div>
  )
}
