import { useQuery } from '@tanstack/react-query'
import { officeClient } from '@/api/officeClient'
import type { SyncStatusResponse } from '@/types/api'
import { formatDistanceToNow } from 'date-fns'
import { it } from 'date-fns/locale'
import { POLLING_INTERVAL } from '@/lib/constants'

export function SyncIndicator({ tabella }: { tabella: string }) {
  const { data } = useQuery({
    queryKey: ['sync', 'status'],
    queryFn: async () => {
      const { data } = await officeClient.get<SyncStatusResponse>('/api/sync/status')
      return data
    },
    refetchInterval: POLLING_INTERVAL.SLOW,
  })

  const tabStatus = data?.tabelle.find(t => t.tabella === tabella)
  if (!tabStatus?.last_sync_at) return null

  const minutesAgo = Math.floor(
    (Date.now() - new Date(tabStatus.last_sync_at).getTime()) / 60_000
  )

  const color =
    tabStatus.last_error ? 'text-red-500' :
    minutesAgo > 30 ? 'text-red-500' :
    minutesAgo > 10 ? 'text-yellow-500' :
    'text-green-500'

  const label = formatDistanceToNow(new Date(tabStatus.last_sync_at), {
    addSuffix: true,
    locale: it,
  })

  return (
    <span className={`text-xs ${color}`}>
      Sync {label}
      {tabStatus.last_error && ' · ⚠ errore'}
    </span>
  )
}
