import { useState, useMemo } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { format, startOfMonth, endOfMonth, addMonths } from 'date-fns'

import { useOrdiniF1a } from '@/hooks/useOrdiniF1a'
import { officeClient } from '@/api/officeClient'
import { useAuthStore } from '@/store/authStore'
import { UrgenzaBadge } from '@/components/UrgenzaBadge'
import { DataConsegnaLabel } from '@/components/DataConsegnaLabel'
import { SyncIndicator } from '@/components/SyncIndicator'
import { ClienteLabel } from '@/components/ClienteLabel'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { extractApiError, downloadExcel, formatQty } from '@/lib/utils'
import type { GeneraCommesseRequest, GeneraCommesseResponse } from '@/types/api'

type FiltroConsegna = 'mese_corrente' | 'mese_prossimo' | 'prossimi_3_mesi' | 'scaduti' | 'tutti'

function getDateRange(filtro: FiltroConsegna): { dataDa?: string; dataA?: string } {
  const oggi = new Date()
  const fmt = (d: Date) => format(d, 'yyyy-MM-dd')
  switch (filtro) {
    case 'mese_corrente':
      return { dataDa: fmt(startOfMonth(oggi)), dataA: fmt(endOfMonth(oggi)) }
    case 'mese_prossimo': {
      const prossimo = addMonths(oggi, 1)
      return { dataDa: fmt(startOfMonth(prossimo)), dataA: fmt(endOfMonth(prossimo)) }
    }
    case 'prossimi_3_mesi':
      return { dataDa: fmt(oggi), dataA: fmt(endOfMonth(addMonths(oggi, 3))) }
    case 'scaduti':
      return { dataA: fmt(oggi) }
    case 'tutti':
    default:
      return {}
  }
}

export default function F1a() {
  const { username } = useAuthStore()
  const queryClient = useQueryClient()

  const [righeSelezionate, setRigheSelezionate] = useState<Set<string>>(new Set())
  const [filtroConsegna, setFiltroConsegna] = useState<FiltroConsegna>('mese_corrente')

  const dateRange = useMemo(() => getDateRange(filtroConsegna), [filtroConsegna])
  const { data: righe, isLoading, isError } = useOrdiniF1a(dateRange)

  const generaCommesse = useMutation({
    mutationFn: async (payload: GeneraCommesseRequest) => {
      const { data } = await officeClient.post<GeneraCommesseResponse>(
        '/api/produzione/genera-commesse',
        payload
      )
      return data
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['produzione', 'f1a'] })
      queryClient.invalidateQueries({ queryKey: ['produzione', 'coda'] })
      setRigheSelezionate(new Set())
      toast.success(`${result.commesse_create} commesse create`)
      downloadExcel(
        result.file_excel_base64,
        `commesse_${new Date().toISOString().slice(0, 10)}.xlsx`
      )
    },
    onError: (err: unknown) => toast.error(extractApiError(err)),
  })

  const toggleRiga = (id: string) => {
    setRigheSelezionate(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleTutte = () => {
    if (!righe) return
    if (righeSelezionate.size === righe.length) {
      setRigheSelezionate(new Set())
    } else {
      setRigheSelezionate(new Set(righe.map(r => r.riga_ordine_id)))
    }
  }

  const handleGeneraCommesse = () => {
    if (!righeSelezionate.size) return
    generaCommesse.mutate({
      righe: Array.from(righeSelezionate).map(id => ({
        riga_ordine_id: id,
        qty_ciclo_corrente: null,
        qty_scorta: 0,
      })),
      created_by: username ?? 'sistema',
    })
  }

  if (isLoading) return <div className="p-6 text-muted-foreground">Caricamento...</div>
  if (isError) return <div className="p-6 text-red-500">Errore nel caricamento dati</div>

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Lancio ordini cliente</h1>
          <SyncIndicator tabella="ordini" />
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={filtroConsegna}
            onValueChange={v => {
              setFiltroConsegna(v as FiltroConsegna)
              setRigheSelezionate(new Set())
            }}
          >
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="mese_corrente">Consegna questo mese</SelectItem>
              <SelectItem value="mese_prossimo">Consegna mese prossimo</SelectItem>
              <SelectItem value="prossimi_3_mesi">Prossimi 3 mesi</SelectItem>
              <SelectItem value="scaduti">Scaduti</SelectItem>
              <SelectItem value="tutti">Tutti</SelectItem>
            </SelectContent>
          </Select>
          <Button
            onClick={handleGeneraCommesse}
            disabled={!righeSelezionate.size || generaCommesse.isPending}
          >
            {generaCommesse.isPending
              ? 'Generazione...'
              : `Genera commesse (${righeSelezionate.size})`}
          </Button>
        </div>
      </div>

      {/* Lista righe */}
      {!righe?.length ? (
        <div className="text-muted-foreground py-12 text-center border rounded-lg">
          Nessuna riga da processare
        </div>
      ) : (
        <div className="border rounded-lg divide-y">
          {/* Header tabella */}
          <div className="flex items-center gap-4 px-4 py-2 bg-muted/50 text-xs font-medium text-muted-foreground">
            <Checkbox
              checked={righeSelezionate.size === righe.length && righe.length > 0}
              onCheckedChange={toggleTutte}
            />
            <span className="flex-1">Articolo · Cliente</span>
            <span className="min-w-[80px] text-right">Consegna</span>
            <span className="min-w-[100px] text-right">Qt da produrre</span>
          </div>

          {righe.map(riga => (
            <div
              key={riga.riga_ordine_id}
              className="flex items-center gap-4 p-4 hover:bg-muted/30 transition-colors cursor-pointer"
              onClick={() => toggleRiga(riga.riga_ordine_id)}
            >
              <Checkbox
                checked={righeSelezionate.has(riga.riga_ordine_id)}
                onCheckedChange={() => toggleRiga(riga.riga_ordine_id)}
                onClick={e => e.stopPropagation()}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{riga.codice_articolo}</span>
                  <UrgenzaBadge attiva={riga.flag_urgenza} />
                  {riga.flag_data_scaduta && (
                    <Badge variant="destructive" className="text-xs">Scaduta</Badge>
                  )}
                </div>
                <div className="text-sm text-muted-foreground truncate">
                  {riga.descrizione_articolo}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  <ClienteLabel cliente={riga.cliente} /> · {riga.numero_ordine}
                </div>
              </div>
              <div className="text-sm text-right min-w-[80px]">
                <DataConsegnaLabel
                  data={riga.data_consegna}
                  flagScaduta={riga.flag_data_scaduta}
                />
              </div>
              <div className="text-sm text-right min-w-[100px]">
                <span className="font-medium">{formatQty(riga.qty_da_produrre)}</span>
                <div className="text-muted-foreground text-xs">
                  mag: {formatQty(riga.giacenza_attuale)} · prod: {formatQty(riga.qty_in_produzione)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
