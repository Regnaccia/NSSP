/**
 * Configurazione categorie articolo — mapping CAT_ART1 EasyJob → famiglia MRS.
 * Le categorie vengono sincronizzate da CATART1 di EasyJob.
 * L'utente assegna ogni categoria a una famiglia (standard / speciali / barre)
 * oppure la lascia senza famiglia per escluderla dai lanci.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { officeClient } from '@/api/officeClient'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { extractApiError } from '@/lib/utils'
import type { CategoriaArticoloResponse } from '@/types/api'

type Famiglia = 'standard' | 'speciali' | 'barre'

const FAMIGLIE: { value: Famiglia; label: string; color: string }[] = [
  { value: 'standard', label: 'Standard',  color: 'bg-blue-100 text-blue-800' },
  { value: 'speciali', label: 'Speciali',  color: 'bg-purple-100 text-purple-800' },
  { value: 'barre',    label: 'Barre',     color: 'bg-amber-100 text-amber-800' },
]

function FamigliaBadge({ famiglia }: { famiglia: string | null }) {
  if (!famiglia) return <span className="text-xs text-muted-foreground">— esclusa</span>
  const f = FAMIGLIE.find(f => f.value === famiglia)
  if (!f) return <Badge variant="secondary">{famiglia}</Badge>
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${f.color}`}>{f.label}</span>
}

export default function Categorie() {
  const queryClient = useQueryClient()

  const { data: categorie, isLoading } = useQuery({
    queryKey: ['categorie'],
    queryFn: () => officeClient.get<CategoriaArticoloResponse[]>('/api/categorie').then(r => r.data),
  })

  const patchCategoria = useMutation({
    mutationFn: ({ codice, famiglia }: { codice: string; famiglia: Famiglia | null }) =>
      officeClient.patch(`/api/categorie/${codice}`, { famiglia }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categorie'] })
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  const conteggioPerFamiglia = FAMIGLIE.map(f => ({
    ...f,
    count: categorie?.filter(c => c.famiglia === f.value).reduce((s, c) => s + c.nr_articoli, 0) ?? 0,
  }))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Configurazione famiglie</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Assegna ogni categoria EasyJob (CAT_ART1) a una famiglia di produzione.
            Le categorie senza famiglia vengono escluse dai lanci.
          </p>
        </div>
        {/* Riepilogo */}
        <div className="flex gap-3">
          {conteggioPerFamiglia.map(f => (
            <div key={f.value} className="text-center">
              <div className={`text-xs font-medium px-2 py-0.5 rounded-full ${f.color}`}>{f.label}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{f.count} art.</div>
            </div>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground py-8 text-center">Caricamento...</div>
      ) : !categorie?.length ? (
        <div className="text-muted-foreground py-12 text-center border rounded-lg">
          Nessuna categoria — esegui una sync per caricare le categorie da EasyJob
        </div>
      ) : (
        <div className="border rounded-lg divide-y">
          {/* Header */}
          <div className="grid grid-cols-[120px_1fr_80px_200px] gap-4 px-4 py-2 bg-muted/50 text-xs font-medium text-muted-foreground">
            <span>Codice</span>
            <span>Descrizione EasyJob</span>
            <span className="text-right">Articoli</span>
            <span>Famiglia MRS</span>
          </div>

          {categorie.map(cat => (
            <div
              key={cat.codice}
              className="grid grid-cols-[120px_1fr_80px_200px] gap-4 px-4 py-2.5 items-center hover:bg-muted/20 text-sm"
            >
              <span className="font-mono font-medium">{cat.codice}</span>
              <span className="text-muted-foreground">{cat.descrizione ?? '—'}</span>
              <span className="text-right tabular-nums text-muted-foreground">{cat.nr_articoli}</span>
              <Select
                value={cat.famiglia ?? '__none__'}
                onValueChange={v =>
                  patchCategoria.mutate({
                    codice: cat.codice,
                    famiglia: v === '__none__' ? null : v as Famiglia,
                  })
                }
              >
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue>
                    <FamigliaBadge famiglia={cat.famiglia} />
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">
                    <span className="text-muted-foreground">— esclusa</span>
                  </SelectItem>
                  {FAMIGLIE.map(f => (
                    <SelectItem key={f.value} value={f.value}>
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium mr-1 ${f.color}`}>
                        {f.label}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
