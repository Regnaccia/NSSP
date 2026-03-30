import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { RefreshCw, CheckCircle, XCircle, AlertCircle, Clock } from 'lucide-react'

import { useSyncStatus } from '@/hooks/useSyncStatus'
import { officeClient } from '@/api/officeClient'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { extractApiError, formatDataOra } from '@/lib/utils'
import type { SyncTabella } from '@/types/api'

function TabellaRow({ t }: { t: SyncTabella }) {
  const ok = !t.last_error
  const mai = !t.last_sync_at

  return (
    <div className="flex items-center gap-4 px-4 py-3 border-b last:border-0">
      {mai ? (
        <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
      ) : ok ? (
        <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
      ) : (
        <XCircle className="h-4 w-4 text-red-500 shrink-0" />
      )}

      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm">{t.tabella}</div>
        {t.last_error && (
          <div className="text-xs text-red-500 truncate">{t.last_error}</div>
        )}
      </div>

      <div className="text-xs text-muted-foreground text-right space-y-0.5">
        <div>{t.last_sync_at ? formatDataOra(t.last_sync_at) : 'Mai sincronizzato'}</div>
        <div>{t.records_updated} record · {t.sync_duration_ms} ms</div>
      </div>
    </div>
  )
}

export default function AdminSync() {
  const queryClient = useQueryClient()
  const { data, isLoading, isError } = useSyncStatus()

  const triggerSync = useMutation({
    mutationFn: async () => {
      await officeClient.post('/api/sync/force-all')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sync', 'status'] })
      toast.success('Sync avviato — aggiornamento in corso')
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError) return <div className="p-6 text-red-500">Errore nel caricamento status sync</div>

  const connesso = data?.easyjob_connesso ?? false
  const tabelle = data?.tabelle ?? []
  const conErrori = tabelle.filter(t => t.last_error).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Stato Sync EasyJob</h1>
        <Button
          onClick={() => triggerSync.mutate()}
          disabled={triggerSync.isPending || !connesso}
          variant="outline"
          size="sm"
        >
          <RefreshCw className={`h-4 w-4 ${triggerSync.isPending ? 'animate-spin' : ''}`} />
          {triggerSync.isPending ? 'Sync in corso...' : 'Forza sync ora'}
        </Button>
      </div>

      {/* Stato connessione */}
      <div className="flex items-center gap-3 p-4 border rounded-lg">
        {connesso ? (
          <CheckCircle className="h-5 w-5 text-green-500" />
        ) : (
          <AlertCircle className="h-5 w-5 text-red-500" />
        )}
        <div>
          <div className="font-medium text-sm">
            EasyJob {connesso ? 'connesso' : 'non raggiungibile'}
          </div>
          {!connesso && (
            <div className="text-xs text-muted-foreground">
              Verificare le credenziali in easy.env e la connessione al server SQL
            </div>
          )}
        </div>
        <div className="ml-auto">
          {conErrori > 0 && (
            <Badge variant="destructive">{conErrori} errori</Badge>
          )}
        </div>
      </div>

      {/* Tabelle */}
      <div>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
          Tabelle sincronizzate
        </h2>
        <div className="border rounded-lg divide-y">
          {tabelle.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground text-sm">
              Nessuna sincronizzazione ancora eseguita
            </div>
          ) : (
            tabelle.map(t => <TabellaRow key={t.tabella} t={t} />)
          )}
        </div>
      </div>
    </div>
  )
}
