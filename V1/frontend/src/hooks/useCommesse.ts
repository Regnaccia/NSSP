import { useQuery } from '@tanstack/react-query'
import { officeClient } from '@/api/officeClient'
import type { CommessaResponse } from '@/types/api'
import { POLLING_INTERVAL } from '@/lib/constants'

export function useCodaProduzione() {
  return useQuery({
    queryKey: ['produzione', 'coda'],
    queryFn: async () => {
      const { data } = await officeClient.get<CommessaResponse[]>('/api/produzione/coda')
      return data
    },
    refetchInterval: POLLING_INTERVAL.OFFICE,
  })
}

export function useMacchineCommesse(macchinaId: string) {
  return useQuery({
    queryKey: ['reparto', 'coda', macchinaId],
    queryFn: async () => {
      const { data } = await officeClient.get<CommessaResponse[]>(
        `/api/reparto/macchine/${macchinaId}/coda`
      )
      return data
    },
    refetchInterval: POLLING_INTERVAL.KIOSK,
    enabled: Boolean(macchinaId),
  })
}
