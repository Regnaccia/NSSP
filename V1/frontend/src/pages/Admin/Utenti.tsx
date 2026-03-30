import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { officeClient } from '@/api/officeClient'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogClose,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Checkbox } from '@/components/ui/checkbox'
import type { UtenteResponse, Ruolo } from '@/types/api'
import { extractApiError, formatData } from '@/lib/utils'
import { LABEL_RUOLO, RUOLI } from '@/lib/constants'
import { Plus, Pencil } from 'lucide-react'

// ─── Tipi locali ──────────────────────────────────────────────────────────────

interface CreaUtenteForm {
  username: string
  password: string
  ruolo: Ruolo
}

interface PatchUtenteForm {
  password?: string
  ruolo?: Ruolo
  attivo?: boolean
}

// ─── Componente ───────────────────────────────────────────────────────────────

export default function AdminUtenti() {
  const queryClient = useQueryClient()
  const [openCrea, setOpenCrea] = useState(false)
  const [editingUtente, setEditingUtente] = useState<UtenteResponse | null>(null)

  // ── Query ──────────────────────────────────────────────────────────────────
  const { data: utenti, isLoading } = useQuery({
    queryKey: ['admin', 'utenti'],
    queryFn: async () => {
      const { data } = await officeClient.get<UtenteResponse[]>('/api/auth/utenti')
      return data
    },
  })

  // ── Mutation: crea utente ──────────────────────────────────────────────────
  const creaUtente = useMutation({
    mutationFn: async (form: CreaUtenteForm) => {
      const { data } = await officeClient.post<UtenteResponse>('/api/auth/utenti', form)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'utenti'] })
      toast.success('Utente creato')
      setOpenCrea(false)
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  // ── Mutation: patch utente ─────────────────────────────────────────────────
  const patchUtente = useMutation({
    mutationFn: async ({ id, patch }: { id: string; patch: PatchUtenteForm }) => {
      const { data } = await officeClient.patch<UtenteResponse>(
        `/api/auth/utenti/${id}`, patch
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'utenti'] })
      toast.success('Utente aggiornato')
      setEditingUtente(null)
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Gestione utenti</h1>
        <Button size="sm" onClick={() => setOpenCrea(true)}>
          <Plus className="h-4 w-4" />
          Nuovo utente
        </Button>
      </div>

      {/* Tabella */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Username</TableHead>
              <TableHead>Ruolo</TableHead>
              <TableHead>Stato</TableHead>
              <TableHead>Creato</TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {utenti?.map(u => (
              <TableRow key={u.id}>
                <TableCell className="font-medium">{u.username}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{LABEL_RUOLO[u.ruolo] ?? u.ruolo}</Badge>
                </TableCell>
                <TableCell>
                  {u.attivo
                    ? <Badge variant="default">Attivo</Badge>
                    : <Badge variant="outline">Disabilitato</Badge>
                  }
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {formatData(u.created_at)}
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setEditingUtente(u)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Dialog: crea utente */}
      <CreaUtenteDialog
        open={openCrea}
        onOpenChange={setOpenCrea}
        onSubmit={(form) => creaUtente.mutate(form)}
        isPending={creaUtente.isPending}
      />

      {/* Dialog: modifica utente */}
      {editingUtente && (
        <EditUtenteDialog
          utente={editingUtente}
          onOpenChange={(open) => { if (!open) setEditingUtente(null) }}
          onSubmit={(patch) => patchUtente.mutate({ id: editingUtente.id, patch })}
          isPending={patchUtente.isPending}
        />
      )}
    </div>
  )
}

// ─── Dialog: crea utente ──────────────────────────────────────────────────────

function CreaUtenteDialog({
  open, onOpenChange, onSubmit, isPending,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  onSubmit: (form: CreaUtenteForm) => void
  isPending: boolean
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [ruolo, setRuolo] = useState<Ruolo>('produzione')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!username || !password) return
    onSubmit({ username, password, ruolo })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nuovo utente</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Username</Label>
            <Input value={username} onChange={e => setUsername(e.target.value)} required />
          </div>
          <div className="space-y-2">
            <Label>Password</Label>
            <Input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label>Ruolo</Label>
            <Select value={ruolo} onValueChange={v => setRuolo(v as Ruolo)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RUOLI.map(r => (
                  <SelectItem key={r} value={r}>{LABEL_RUOLO[r]}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">Annulla</Button>
            </DialogClose>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Creazione...' : 'Crea utente'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── Dialog: modifica utente ──────────────────────────────────────────────────

function EditUtenteDialog({
  utente, onOpenChange, onSubmit, isPending,
}: {
  utente: UtenteResponse
  onOpenChange: (v: boolean) => void
  onSubmit: (patch: PatchUtenteForm) => void
  isPending: boolean
}) {
  const [password, setPassword] = useState('')
  const [ruolo, setRuolo] = useState<Ruolo>(utente.ruolo)
  const [attivo, setAttivo] = useState(utente.attivo)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const patch: PatchUtenteForm = { ruolo, attivo }
    if (password) patch.password = password
    onSubmit(patch)
  }

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Modifica — {utente.username}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Nuova password (lascia vuoto per non cambiare)</Label>
            <Input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <div className="space-y-2">
            <Label>Ruolo</Label>
            <Select value={ruolo} onValueChange={v => setRuolo(v as Ruolo)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RUOLI.map(r => (
                  <SelectItem key={r} value={r}>{LABEL_RUOLO[r]}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="attivo"
              checked={attivo}
              onCheckedChange={v => setAttivo(Boolean(v))}
            />
            <Label htmlFor="attivo">Utente attivo</Label>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">Annulla</Button>
            </DialogClose>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Salvataggio...' : 'Salva'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
