import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, addDays, startOfWeek, eachDayOfInterval } from 'date-fns'
import { it } from 'date-fns/locale'
import { ChevronLeft, ChevronRight } from 'lucide-react'

import { officeClient } from '@/api/officeClient'
import { SpedizioneStatusBadge } from '@/components/SpedizioneStatusBadge'
import { ClienteLabel } from '@/components/ClienteLabel'
import { Button } from '@/components/ui/button'
import { POLLING_INTERVAL } from '@/lib/constants'
import type { CalendarioGiornoItem } from '@/types/api'

export default function F3c() {
  const [baseDate, setBaseDate] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))

  const dataDa = format(baseDate, 'yyyy-MM-dd')
  const dataA = format(addDays(baseDate, 13), 'yyyy-MM-dd')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['logistica', 'calendario', { dataDa, dataA }],
    queryFn: async () => {
      const { data } = await officeClient.get<CalendarioGiornoItem[]>('/api/logistica/calendario', {
        params: { data_da: dataDa, data_a: dataA },
      })
      return data
    },
    refetchInterval: POLLING_INTERVAL.SLOW,
  })

  // Mappa data → spedizioni
  const byDate = new Map<string, CalendarioGiornoItem>()
  data?.forEach(g => byDate.set(g.data, g))

  const days = eachDayOfInterval({ start: baseDate, end: addDays(baseDate, 13) })

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError) return <div className="p-6 text-red-500">Errore nel caricamento calendario</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Calendario spedizioni</h1>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setBaseDate(d => addDays(d, -14))}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium min-w-[180px] text-center">
            {format(baseDate, 'd MMM', { locale: it })} — {format(addDays(baseDate, 13), 'd MMM yyyy', { locale: it })}
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setBaseDate(d => addDays(d, 14))}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-2">
        {/* Intestazione giorni settimana */}
        {['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'].map(g => (
          <div key={g} className="text-xs font-semibold text-muted-foreground text-center py-1">
            {g}
          </div>
        ))}

        {/* 14 giorni su 2 righe */}
        {days.map(day => {
          const key = format(day, 'yyyy-MM-dd')
          const spedizioni = byDate.get(key)?.spedizioni ?? []
          const isToday = format(day, 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd')
          const isWeekend = day.getDay() === 0 || day.getDay() === 6

          return (
            <div
              key={key}
              className={`min-h-[100px] border rounded-lg p-2 space-y-1 ${
                isToday ? 'border-primary bg-primary/5' :
                isWeekend ? 'bg-muted/30' :
                'bg-background'
              }`}
            >
              <div className={`text-xs font-medium ${isToday ? 'text-primary' : 'text-foreground'}`}>
                {format(day, 'd', { locale: it })}
                <span className="text-muted-foreground ml-1">
                  {format(day, 'MMM', { locale: it })}
                </span>
              </div>
              {spedizioni.map(s => (
                <div key={s.id} className="text-xs border rounded px-1.5 py-0.5 bg-background space-y-0.5">
                  <div className="font-medium truncate">{s.numero_ordine ?? '—'}</div>
                  <ClienteLabel cliente={s.cliente} className="text-muted-foreground truncate block" />
                  <SpedizioneStatusBadge stato={s.stato} />
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
