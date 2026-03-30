import { useQuery } from '@tanstack/react-query'
import { UrgenzaBadge } from '@/components/UrgenzaBadge'
import { DataConsegnaLabel } from '@/components/DataConsegnaLabel'
import { ClienteLabel } from '@/components/ClienteLabel'
import { Badge } from '@/components/ui/badge'
import { officeClient } from '@/api/officeClient'
import { POLLING_INTERVAL, LABEL_TIPO_POLICY } from '@/lib/constants'
import type { OrdineSpedireResponse } from '@/types/api'
import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function F3a() {
  const navigate = useNavigate()

  const { data: ordini, isLoading, isError } = useQuery({
    queryKey: ['logistica', 'da-spedire'],
    queryFn: async () => {
      const { data } = await officeClient.get<OrdineSpedireResponse[]>('/api/logistica/da-spedire')
      return data
    },
    refetchInterval: POLLING_INTERVAL.OFFICE,
  })

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError) return <div className="p-6 text-red-500">Errore nel caricamento dati</div>

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Da spedire</h1>
        <p className="text-sm text-muted-foreground">
          Ordini pronti in magazzino in attesa di spedizione
        </p>
      </div>

      {!ordini?.length ? (
        <div className="text-muted-foreground py-12 text-center border rounded-lg">
          Nessun ordine da spedire
        </div>
      ) : (
        <div className="border rounded-lg divide-y">
          {ordini.map(o => (
            <div key={o.ordine_id} className="flex items-center gap-4 p-4 hover:bg-muted/30 transition-colors">
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">{o.numero_ordine}</span>
                  <ClienteLabel cliente={o.cliente} className="text-sm text-muted-foreground" />
                  <UrgenzaBadge attiva={o.flag_urgenza} />
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <DataConsegnaLabel data={o.data_consegna} />
                  <Badge variant="secondary" className="text-xs">
                    {LABEL_TIPO_POLICY[o.tipo_policy] ?? o.tipo_policy}
                  </Badge>
                  {o.corriere_suggerito && (
                    <span className="text-muted-foreground text-xs">
                      Corriere: {o.corriere_suggerito}
                    </span>
                  )}
                  {o.data_spedizione_suggerita && (
                    <span className="text-muted-foreground text-xs">
                      Spedire entro: <DataConsegnaLabel data={o.data_spedizione_suggerita} />
                    </span>
                  )}
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/logistica/f3b')}
              >
                <ArrowRight className="h-4 w-4" />
                Pianifica spedizione
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
