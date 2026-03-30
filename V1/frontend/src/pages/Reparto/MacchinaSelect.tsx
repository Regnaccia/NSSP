import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Wrench } from 'lucide-react'

import { kioskClient } from '@/api/kioskClient'
import type { MacchinaResponse } from '@/types/api'

const STATO_COLOR: Record<string, string> = {
  disponibile:     'bg-green-100 border-green-300 text-green-800',
  in_lavorazione:  'bg-blue-100 border-blue-300 text-blue-800',
  in_setup:        'bg-yellow-100 border-yellow-300 text-yellow-800',
  in_manutenzione: 'bg-red-100 border-red-300 text-red-800',
}

const LABEL_STATO: Record<string, string> = {
  disponibile:     'Disponibile',
  in_lavorazione:  'In lavorazione',
  in_setup:        'In setup',
  in_manutenzione: 'In manutenzione',
}

export default function MacchinaSelect() {
  const navigate = useNavigate()

  const { data: macchine, isLoading, isError } = useQuery({
    queryKey: ['reparto', 'macchine'],
    queryFn: async () => {
      const { data } = await kioskClient.get<MacchinaResponse[]>('/api/reparto/macchine')
      return data
    },
    refetchInterval: 30_000,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-muted-foreground">Caricamento macchine...</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-red-500">Errore di connessione — riprovare</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 gap-8">
      <div className="text-center space-y-2">
        <Wrench className="h-12 w-12 text-primary mx-auto" />
        <h1 className="text-3xl font-bold">Seleziona macchina</h1>
        <p className="text-lg text-muted-foreground">Tocca la macchina su cui stai lavorando</p>
      </div>

      <div className="grid grid-cols-2 gap-4 w-full max-w-2xl sm:grid-cols-3">
        {macchine?.map(m => (
          <button
            key={m.id}
            onClick={() => navigate(`/reparto/${m.id}`)}
            className={`border-2 rounded-xl p-6 text-left transition-all active:scale-95 ${STATO_COLOR[m.stato] ?? 'bg-gray-100 border-gray-300'}`}
          >
            <div className="text-2xl font-bold">{m.codice}</div>
            <div className="text-base font-medium mt-1">{m.nome}</div>
            <div className="text-sm mt-2 opacity-75">{LABEL_STATO[m.stato] ?? m.stato}</div>
            {m.setup_corrente && (
              <div className="text-xs mt-1 opacity-60 truncate">{m.setup_corrente}</div>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
