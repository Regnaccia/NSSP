import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Settings } from 'lucide-react'

import { officeClient } from '@/api/officeClient'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogClose,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { extractApiError } from '@/lib/utils'
import { LABEL_TIPO_POLICY } from '@/lib/constants'
import type { ClienteResponse, PolicyClienteResponse, TipoPolicy } from '@/types/api'

export default function Clienti() {
  const queryClient = useQueryClient()
  const [policyCliente, setPolicyCliente] = useState<ClienteResponse | null>(null)

  const { data: clienti, isLoading } = useQuery({
    queryKey: ['logistica', 'clienti'],
    queryFn: async () => {
      const { data } = await officeClient.get<ClienteResponse[]>('/api/logistica/clienti')
      return data
    },
  })

  const patchNickname = useMutation({
    mutationFn: async ({ id, nickname }: { id: string; nickname: string }) => {
      const { data } = await officeClient.patch<ClienteResponse>(`/api/logistica/clienti/${id}`, {
        nickname: nickname || null,
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistica', 'clienti'] })
      toast.success('Nickname aggiornato')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Clienti</h1>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Codice</TableHead>
              <TableHead>Ragione Sociale</TableHead>
              <TableHead>Nickname</TableHead>
              <TableHead>Policy</TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {clienti?.map(c => (
              <ClienteRow
                key={c.id}
                cliente={c}
                onEditPolicy={() => setPolicyCliente(c)}
                onSaveNickname={(nickname) => patchNickname.mutate({ id: c.id, nickname })}
              />
            ))}
          </TableBody>
        </Table>
      </div>

      {policyCliente && (
        <PolicyDialog
          cliente={policyCliente}
          onOpenChange={(open) => { if (!open) setPolicyCliente(null) }}
        />
      )}
    </div>
  )
}

function ClienteRow({
  cliente: c, onEditPolicy, onSaveNickname,
}: {
  cliente: ClienteResponse
  onEditPolicy: () => void
  onSaveNickname: (nickname: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [nickname, setNickname] = useState(c.nickname ?? '')

  const { data: policy } = useQuery({
    queryKey: ['logistica', 'policy', c.id],
    queryFn: async () => {
      try {
        const { data } = await officeClient.get<PolicyClienteResponse>(
          `/api/logistica/clienti/${c.id}/policy`
        )
        return data
      } catch {
        return null
      }
    },
  })

  if (editing) {
    return (
      <TableRow>
        <TableCell>{c.codice}</TableCell>
        <TableCell>{c.ragione_sociale}</TableCell>
        <TableCell colSpan={2}>
          <div className="flex gap-2">
            <Input
              value={nickname}
              onChange={e => setNickname(e.target.value)}
              className="h-8 w-44"
              autoFocus
            />
            <Button size="sm" onClick={() => { onSaveNickname(nickname); setEditing(false) }}>
              Salva
            </Button>
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
              Annulla
            </Button>
          </div>
        </TableCell>
        <TableCell />
      </TableRow>
    )
  }

  return (
    <TableRow>
      <TableCell className="font-mono text-sm">{c.codice}</TableCell>
      <TableCell>{c.ragione_sociale}</TableCell>
      <TableCell>
        <button
          className="text-sm text-left hover:underline text-muted-foreground"
          onClick={() => setEditing(true)}
        >
          {c.nickname ?? '— aggiungi nickname'}
        </button>
      </TableCell>
      <TableCell>
        {policy ? (
          <Badge variant="secondary">{LABEL_TIPO_POLICY[policy.tipo_policy] ?? policy.tipo_policy}</Badge>
        ) : (
          <span className="text-muted-foreground text-sm">Non configurata</span>
        )}
      </TableCell>
      <TableCell>
        <Button variant="ghost" size="icon" onClick={onEditPolicy}>
          <Settings className="h-4 w-4" />
        </Button>
      </TableCell>
    </TableRow>
  )
}

function PolicyDialog({ cliente, onOpenChange }: {
  cliente: ClienteResponse
  onOpenChange: (v: boolean) => void
}) {
  const queryClient = useQueryClient()

  const { data: policy } = useQuery({
    queryKey: ['logistica', 'policy', cliente.id],
    queryFn: async () => {
      try {
        const { data } = await officeClient.get<PolicyClienteResponse>(
          `/api/logistica/clienti/${cliente.id}/policy`
        )
        return data
      } catch {
        return null
      }
    },
  })

  const [tipoPolicy, setTipoPolicy] = useState<TipoPolicy>(policy?.tipo_policy ?? 'DEFAULT')
  const [giornoFisso, setGiornoFisso] = useState(policy?.giorno_fisso?.toString() ?? '')
  const [sogliaValore, setSogliaValore] = useState(policy?.soglia_valore?.toString() ?? '')
  const [corriere, setCorriere] = useState(policy?.corriere_preferito ?? '')
  const [note, setNote] = useState(policy?.note_spedizione ?? '')

  const salvaPolicy = useMutation({
    mutationFn: async () => {
      const payload = {
        tipo_policy: tipoPolicy,
        giorno_fisso: giornoFisso ? parseInt(giornoFisso) : null,
        soglia_valore: sogliaValore ? parseFloat(sogliaValore) : null,
        corriere_preferito: corriere || null,
        note_spedizione: note || null,
      }
      const { data } = await officeClient.put<PolicyClienteResponse>(
        `/api/logistica/clienti/${cliente.id}/policy`, payload
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistica', 'policy', cliente.id] })
      toast.success('Policy aggiornata')
      onOpenChange(false)
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Policy spedizione — {cliente.nickname ?? cliente.ragione_sociale}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Tipo policy</Label>
            <Select value={tipoPolicy} onValueChange={v => setTipoPolicy(v as TipoPolicy)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {(Object.keys(LABEL_TIPO_POLICY) as TipoPolicy[]).map(k => (
                  <SelectItem key={k} value={k}>{LABEL_TIPO_POLICY[k]}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {tipoPolicy === 'GIORNO_FISSO' && (
            <div className="space-y-2">
              <Label>Giorno della settimana (1=Lun … 7=Dom)</Label>
              <Input type="number" min={1} max={7} value={giornoFisso} onChange={e => setGiornoFisso(e.target.value)} />
            </div>
          )}
          {tipoPolicy === 'SOGLIA_VALORE' && (
            <div className="space-y-2">
              <Label>Soglia valore (€)</Label>
              <Input type="number" min={0} step={0.01} value={sogliaValore} onChange={e => setSogliaValore(e.target.value)} />
            </div>
          )}
          <div className="space-y-2">
            <Label>Corriere preferito</Label>
            <Input value={corriere} onChange={e => setCorriere(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Note spedizione</Label>
            <Textarea value={note} onChange={e => setNote(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <DialogClose asChild><Button variant="outline">Annulla</Button></DialogClose>
          <Button onClick={() => salvaPolicy.mutate()} disabled={salvaPolicy.isPending}>
            {salvaPolicy.isPending ? 'Salvataggio...' : 'Salva policy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
