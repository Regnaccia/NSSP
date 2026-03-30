import { useQuery } from '@tanstack/react-query'
import { officeClient } from '@/api/officeClient'
import type { EventoResponse, TipoEvento, StatoEvento } from '@/types/api'
import { POLLING_INTERVAL } from '@/lib/constants'

interface EventiParams {
  tipo?: TipoEvento
  stato?: StatoEvento
  destinatario?: string
  refOrdineId?: string
}

export function useEventi(params: EventiParams = {}) {
  return useQuery({
    queryKey: ['eventi', params],
    queryFn: async () => {
      const { data } = await officeClient.get<EventoResponse[]>('/api/eventi', {
        params: {
          tipo: params.tipo || undefined,
          stato: params.stato || undefined,
          destinatario: params.destinatario || undefined,
          ref_ordine_id: params.refOrdineId || undefined,
        },
      })
      return data
    },
    refetchInterval: POLLING_INTERVAL.OFFICE,
  })
}
