import { useQuery } from '@tanstack/react-query'
import { officeClient } from '@/api/officeClient'
import type { SyncStatusResponse } from '@/types/api'
import { POLLING_INTERVAL } from '@/lib/constants'

export function useSyncStatus() {
  return useQuery({
    queryKey: ['sync', 'status'],
    queryFn: async () => {
      const { data } = await officeClient.get<SyncStatusResponse>('/api/sync/status')
      return data
    },
    refetchInterval: POLLING_INTERVAL.SLOW,
  })
}
