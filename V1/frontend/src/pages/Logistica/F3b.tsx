import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, Pencil, CheckCircle } from 'lucide-react'

import { officeClient } from '@/api/officeClient'
import { SpedizioneStatusBadge } from '@/components/SpedizioneStatusBadge'
import { ClienteLabel } from '@/components/ClienteLabel'
import { DataConsegnaLabel } from '@/components/DataConsegnaLabel'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogClose,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { extractApiError, formatData, formatPeso } from '@/lib/utils'
import { POLLING_INTERVAL } from '@/lib/constants'
import type { SpedizioneResponse } from '@/types/api'

interface CreaSpedizioneForm {
  ordine_id: string
  tipo: 'totale' | 'parziale'
  corriere?: string
  data_pianificata?: string
  colli?: number
  peso_kg?: number
  note?: string
}

interface PatchSpedizioneForm {
  corriere?: string
  data_pianificata?: string
  colli?: number
  peso_kg?: number
  note?: string
}

export default function F3b() {
  const queryClient = useQueryClient()
  const [openCrea, setOpenCrea] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [statoFilter, setStatoFilter] = useState<string>('in_preparazione')

  const { data: spedizioni, isLoading, isError } = useQuery({
    queryKey: ['logistica', 'spedizioni', { stato: statoFilter }],
    queryFn: async () => {
      const { data } = await officeClient.get<SpedizioneResponse[]>('/api/logistica/spedizioni', {
        params: { stato: statoFilter !== 'tutte' ? statoFilter : undefined },
      })
      return data
    },
    refetchInterval: POLLING_INTERVAL.OFFICE,
  })

  const creaSpedizione = useMutation({
    mutationFn: async (form: CreaSpedizioneForm) => {
      const { data } = await officeClient.post<SpedizioneResponse>('/api/logistica/spedizioni', form)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistica', 'spedizioni'] })
      toast.success('Spedizione creata')
      setOpenCrea(false)
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  const segnaMutation = useMutation({
    mutationFn: async (id: string) => {
      await officeClient.post(`/api/logistica/spedizioni/${id}/segna-spedita`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistica', 'spedizioni'] })
      queryClient.invalidateQueries({ queryKey: ['logistica', 'calendario'] })
      toast.success('Spedizione registrata come spedita')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  const patchMutation = useMutation({
    mutationFn: async ({ id, patch }: { id: string; patch: PatchSpedizioneForm }) => {
      const { data } = await officeClient.patch<SpedizioneResponse>(
        `/api/logistica/spedizioni/${id}`, patch
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistica', 'spedizioni'] })
      toast.success('Spedizione aggiornata')
      setEditingId(null)
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  const editingSpedizione = spedizioni?.find(s => s.id === editingId) ?? null

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError) return <div className="p-6 text-red-500">Errore nel caricamento dati</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Spedizioni pianificate</h1>
        <div className="flex gap-2">
          <Select value={statoFilter} onValueChange={setStatoFilter}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tutte">Tutti gli stati</SelectItem>
              <SelectItem value="in_preparazione">In preparazione</SelectItem>
              <SelectItem value="spedita">Spedite</SelectItem>
              <SelectItem value="annullata">Annullate</SelectItem>
            </SelectContent>
          </Select>
          <Button size="sm" onClick={() => setOpenCrea(true)}>
            <Plus className="h-4 w-4" />
            Nuova spedizione
          </Button>
        </div>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ordine</TableHead>
              <TableHead>Cliente</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Stato</TableHead>
              <TableHead>Data pianificata</TableHead>
              <TableHead>Corriere</TableHead>
              <TableHead>Colli / Peso</TableHead>
              <TableHead className="w-20" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {!spedizioni?.length ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                  Nessuna spedizione
                </TableCell>
              </TableRow>
            ) : (
              spedizioni.map(s => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.numero_ordine ?? '—'}</TableCell>
                  <TableCell><ClienteLabel cliente={s.cliente} /></TableCell>
                  <TableCell className="text-sm capitalize">{s.tipo}</TableCell>
                  <TableCell><SpedizioneStatusBadge stato={s.stato} /></TableCell>
                  <TableCell><DataConsegnaLabel data={s.data_pianificata} /></TableCell>
                  <TableCell className="text-sm text-muted-foreground">{s.corriere ?? '—'}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {s.colli != null ? `${s.colli} colli` : '—'}
                    {s.peso_kg != null && ` · ${formatPeso(s.peso_kg)}`}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {s.stato === 'in_preparazione' && (
                        <>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Segna come spedita"
                            onClick={() => segnaMutation.mutate(s.id)}
                          >
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setEditingId(s.id)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Dialog crea spedizione */}
      {openCrea && (
        <CreaSpedizioneDialog
          onOpenChange={setOpenCrea}
          onSubmit={(form) => creaSpedizione.mutate(form)}
          isPending={creaSpedizione.isPending}
        />
      )}

      {/* Dialog modifica spedizione */}
      {editingSpedizione && (
        <EditSpedizioneDialog
          spedizione={editingSpedizione}
          onOpenChange={(open) => { if (!open) setEditingId(null) }}
          onSubmit={(patch) => patchMutation.mutate({ id: editingSpedizione.id, patch })}
          isPending={patchMutation.isPending}
        />
      )}
    </div>
  )
}

function CreaSpedizioneDialog({ onOpenChange, onSubmit, isPending }: {
  onOpenChange: (v: boolean) => void
  onSubmit: (form: CreaSpedizioneForm) => void
  isPending: boolean
}) {
  const [ordineId, setOrdineId] = useState('')
  const [tipo, setTipo] = useState<'totale' | 'parziale'>('totale')
  const [corriere, setCorriere] = useState('')
  const [dataPianificata, setDataPianificata] = useState('')
  const [colli, setColli] = useState('')
  const [peso, setPeso] = useState('')
  const [note, setNote] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!ordineId) return
    onSubmit({
      ordine_id: ordineId,
      tipo,
      corriere: corriere || undefined,
      data_pianificata: dataPianificata || undefined,
      colli: colli ? parseInt(colli) : undefined,
      peso_kg: peso ? parseFloat(peso) : undefined,
      note: note || undefined,
    })
  }

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Nuova spedizione</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3 py-2">
          <div className="space-y-1"><Label>Ordine ID</Label>
            <Input value={ordineId} onChange={e => setOrdineId(e.target.value)} required placeholder="UUID ordine" />
          </div>
          <div className="space-y-1"><Label>Tipo</Label>
            <Select value={tipo} onValueChange={v => setTipo(v as 'totale' | 'parziale')}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="totale">Totale</SelectItem>
                <SelectItem value="parziale">Parziale</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1"><Label>Data pianificata</Label>
              <Input type="date" value={dataPianificata} onChange={e => setDataPianificata(e.target.value)} />
            </div>
            <div className="space-y-1"><Label>Corriere</Label>
              <Input value={corriere} onChange={e => setCorriere(e.target.value)} />
            </div>
            <div className="space-y-1"><Label>Colli</Label>
              <Input type="number" min="0" value={colli} onChange={e => setColli(e.target.value)} />
            </div>
            <div className="space-y-1"><Label>Peso (kg)</Label>
              <Input type="number" min="0" step="0.1" value={peso} onChange={e => setPeso(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1"><Label>Note</Label>
            <Textarea value={note} onChange={e => setNote(e.target.value)} />
          </div>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Annulla</Button></DialogClose>
            <Button type="submit" disabled={isPending}>{isPending ? 'Creazione...' : 'Crea'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function EditSpedizioneDialog({ spedizione: s, onOpenChange, onSubmit, isPending }: {
  spedizione: SpedizioneResponse
  onOpenChange: (v: boolean) => void
  onSubmit: (patch: PatchSpedizioneForm) => void
  isPending: boolean
}) {
  const [corriere, setCorriere] = useState(s.corriere ?? '')
  const [dataPianificata, setDataPianificata] = useState(s.data_pianificata?.slice(0, 10) ?? '')
  const [colli, setColli] = useState(s.colli?.toString() ?? '')
  const [peso, setPeso] = useState(s.peso_kg?.toString() ?? '')
  const [note, setNote] = useState(s.note ?? '')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      corriere: corriere || undefined,
      data_pianificata: dataPianificata || undefined,
      colli: colli ? parseInt(colli) : undefined,
      peso_kg: peso ? parseFloat(peso) : undefined,
      note: note || undefined,
    })
  }

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Modifica spedizione — {s.numero_ordine}</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1"><Label>Data pianificata</Label>
              <Input type="date" value={dataPianificata} onChange={e => setDataPianificata(e.target.value)} />
            </div>
            <div className="space-y-1"><Label>Corriere</Label>
              <Input value={corriere} onChange={e => setCorriere(e.target.value)} />
            </div>
            <div className="space-y-1"><Label>Colli</Label>
              <Input type="number" min="0" value={colli} onChange={e => setColli(e.target.value)} />
            </div>
            <div className="space-y-1"><Label>Peso (kg)</Label>
              <Input type="number" min="0" step="0.1" value={peso} onChange={e => setPeso(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1"><Label>Note</Label>
            <Textarea value={note} onChange={e => setNote(e.target.value)} />
          </div>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Annulla</Button></DialogClose>
            <Button type="submit" disabled={isPending}>{isPending ? 'Salvataggio...' : 'Salva'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
