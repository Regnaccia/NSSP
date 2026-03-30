import { useQuery } from '@tanstack/react-query'
import { officeClient } from '@/api/officeClient'
import type { RigaF1aResponse } from '@/types/api'
import { POLLING_INTERVAL } from '@/lib/constants'

interface F1aParams {
  clienteId?: string
  urgenzaOnly?: boolean
  dataDa?: string
  dataA?: string
}

export function useOrdiniF1a(params: F1aParams = {}) {
  return useQuery({
    queryKey: ['produzione', 'f1a', params],
    queryFn: async () => {
      const { data } = await officeClient.get<RigaF1aResponse[]>(
        '/api/produzione/f1a',
        {
          params: {
            cliente_id: params.clienteId || undefined,
            urgenza_only: params.urgenzaOnly || undefined,
            data_da: params.dataDa || undefined,
            data_a: params.dataA || undefined,
          },
        }
      )
      return data
    },
    refetchInterval: POLLING_INTERVAL.OFFICE,
  })
}
