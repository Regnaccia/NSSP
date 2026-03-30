/**
 * Modal di dettaglio e lancio per F1a / F1b.
 *
 * Sezione MAGAZZINO (read-only): giacenza, impegni, in produzione, disp futura, capienza.
 * Sezione PRODUZIONE (editabile): materia prima (override con ricerca), tipo, multipli taglio,
 *   mm materiale, lunghezza barra, nr lotti × pezzi/lotto = qty (live, rosso se supera capienza).
 * Tabella IMPEGNI + tabella PRODUZIONI ATTIVE (lazy, caricate all'apertura).
 */
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'

import { officeClient } from '@/api/officeClient'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import MateriaPrimaCombobox, { type MateriaPrimaOption } from '@/components/MateriaPrimaCombobox'
import { formatQty } from '@/lib/utils'
import type { ImpegniProduzioniResponse, TipoProduzione } from '@/types/api'

const TIPO_PRODUZIONE_OPTIONS: TipoProduzione[] = ['PEZZO', 'BARRA', 'FASCI']

// ─── Calcolo lotti (speculare a utils.py backend) ─────────────────────────────

function calcolaLotti(
  qtyTarget: number,
  tipoProduzione: string,
  multipliTaglio: number | null,
  mmMateriale: number | null,
  lunghezzaBarra: number | null,
): { nrLotti: number; pezziPerLotto: number; qtySuggerita: number } {
  if (qtyTarget <= 0) return { nrLotti: 0, pezziPerLotto: 0, qtySuggerita: 0 }
  const mult = multipliTaglio || 1
  let pezziPerLotto: number
  if (
    ['BARRA', 'FASCI'].includes(tipoProduzione)
    && mmMateriale && mmMateriale > 0
    && lunghezzaBarra && lunghezzaBarra > 0
  ) {
    const pezziPerBarra = Math.floor(lunghezzaBarra / mmMateriale)
    pezziPerLotto = Math.max(1, pezziPerBarra * mult)
  } else {
    pezziPerLotto = Math.max(1, mult)
  }
  const nrLotti = Math.ceil(qtyTarget / pezziPerLotto)
  return { nrLotti, pezziPerLotto, qtySuggerita: nrLotti * pezziPerLotto }
}

// ─── Tipi props ───────────────────────────────────────────────────────────────

export type LancioModalProps = {
  // Articolo
  articoloId: string
  codice: string
  descrizione: string | null
  // Target qty (qty_da_produrre per F1a, qty_da_produrre_scorta per F1b)
  qtyTarget: number
  // Parametri produzione default (da articoli + materie_prime)
  tipoProduzione: TipoProduzione
  multipliTaglio: number | null
  mmMateriale: number | null
  lunghezzaBarra: number | null          // override manuale sull'articolo
  lunghezzaEffettiva: number | null     // = lunghezza_barra ?? materia_prima.lunghezza_mm
  materiaPrimaId: string | null
  materiaPrimaCodice: string | null
  capienza: number | null
  flagNoMateria: boolean
  // qtyOverride attuale (se già confermato in precedenza)
  qtyOverride?: number | null
  // Callback
  onConferma: (qty: number) => void   // salva override nella lista
  onLanciaSubito?: (qty: number) => void  // lancio immediato singolo (opzionale)
  onClose: () => void
}

// ─── Componente ───────────────────────────────────────────────────────────────

export default function LancioModal({
  articoloId,
  codice,
  descrizione,
  qtyTarget,
  tipoProduzione: tipoProdDefault,
  multipliTaglio: multipliTaglioDefault,
  mmMateriale: mmMaterialeDefault,
  lunghezzaBarra: lunghezzaBarraDefault,
  lunghezzaEffettiva: lunghezzaEffettivaDefault,
  materiaPrimaId,
  materiaPrimaCodice,
  capienza,
  flagNoMateria,
  qtyOverride,
  onConferma,
  onLanciaSubito,
  onClose,
}: LancioModalProps) {

  // ── Stato materia prima override ────────────────────────────────────────────
  const initMp: MateriaPrimaOption | null = materiaPrimaId
    ? { id: materiaPrimaId, codice: materiaPrimaCodice ?? '', descrizione: null, lunghezza_mm: lunghezzaEffettivaDefault }
    : null
  const [mpOverride, setMpOverride] = useState<MateriaPrimaOption | null>(null)
  const effMp = mpOverride ?? initMp

  // Effective values (considerando override materia prima)
  const effLunghezzaMp = mpOverride !== null ? mpOverride.lunghezza_mm : lunghezzaEffettivaDefault
  const effFlagNoMateria = effMp === null

  // Warning: materia prima configurata ma lunghezza mancante (e nessun override manuale)
  const effFlagLunghezzaMancante = !effFlagNoMateria && !effLunghezzaMp

  // ── Stato editabile sezione produzione ──────────────────────────────────────
  const [tipoProd, setTipoProd] = useState<TipoProduzione>(tipoProdDefault)
  const [multipliTaglio, setMultipliTaglio] = useState<string>(
    String(multipliTaglioDefault ?? '')
  )
  const [mmMateriale, setMmMateriale] = useState<string>(
    String(mmMaterialeDefault ?? '')
  )
  // Lunghezza: parte da quella effettiva (materia prima o override manuale), modificabile in sessione
  const [lunghezzaBarra, setLunghezzaBarra] = useState<string>(
    String(lunghezzaEffettivaDefault ?? lunghezzaBarraDefault ?? '')
  )

  // Quando cambia la materia prima override, aggiorna la lunghezza
  useEffect(() => {
    if (mpOverride !== null) {
      setLunghezzaBarra(String(mpOverride.lunghezza_mm ?? ''))
    }
  }, [mpOverride?.id])

  // Se c'è già un override confermato, pre-popola nr lotti di conseguenza
  const calcolatoDefault = calcolaLotti(qtyTarget, tipoProdDefault, multipliTaglioDefault, mmMaterialeDefault, lunghezzaBarraDefault)
  const nrLottiIniziale = qtyOverride != null && calcolatoDefault.pezziPerLotto > 0
    ? String(Math.ceil(qtyOverride / calcolatoDefault.pezziPerLotto))
    : ''
  const [nrLottiOverride, setNrLottiOverride] = useState<string>(nrLottiIniziale)

  // Calcolo live
  const mt = parseInt(multipliTaglio) || null
  const mm = parseInt(mmMateriale) || null
  const lb = parseInt(lunghezzaBarra) || null
  const calcolato = calcolaLotti(qtyTarget, tipoProd, mt, mm, lb)
  const nrLotti = nrLottiOverride !== '' ? (parseInt(nrLottiOverride) || 0) : calcolato.nrLotti
  const { pezziPerLotto } = calcolato
  const qtySuggerita = nrLotti * pezziPerLotto

  const isModificato = qtySuggerita !== calcolatoDefault.qtySuggerita
    || tipoProd !== tipoProdDefault
    || mpOverride !== null

  // Reset nr lotti quando cambiano i parametri di calcolo
  useEffect(() => { setNrLottiOverride('') }, [tipoProd, multipliTaglio, mmMateriale, lunghezzaBarra])

  // ── Carica impegni + produzioni ─────────────────────────────────────────────
  const { data: dettaglio, isLoading: dettaglioLoading } = useQuery({
    queryKey: ['articoli', articoloId, 'impegni-produzioni'],
    queryFn: async () => {
      const { data } = await officeClient.get<ImpegniProduzioniResponse>(
        `/api/articoli/${articoloId}/impegni-produzioni`
      )
      return data
    },
  })

  const supera = capienza != null && dettaglio != null
    && (qtySuggerita + dettaglio.qty_disponibile_futura) > capienza

  const fmtData = (d: string | null) =>
    d ? format(new Date(d), 'dd/MM/yy') : '—'

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-mono text-base">
            {codice}
            <span className="ml-2 font-sans font-normal text-sm text-muted-foreground">
              {descrizione}
            </span>
          </DialogTitle>
        </DialogHeader>

        {/* ── SEZIONI MAGAZZINO + PRODUZIONE ────────────────────────── */}
        <div className="grid grid-cols-2 gap-4">

          {/* MAGAZZINO */}
          <div className="border rounded-md p-3 space-y-2 bg-amber-50/50">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              Magazzino
            </div>
            <Row label="Giacenza attuale" value={formatQty(dettaglio?.giacenza_attuale ?? 0)} />
            <Row label="Impegni aperti"   value={formatQty(dettaglio?.impegni_totali ?? 0)} />
            <Row label="In produzione"    value={formatQty(dettaglio?.in_produzione ?? 0)} />
            <Row
              label="Disp futura"
              value={formatQty(dettaglio?.qty_disponibile_futura ?? 0)}
              highlight={dettaglio != null && dettaglio.qty_disponibile_futura <= 0}
            />
            {capienza != null && (
              <Row label="Capienza max" value={formatQty(capienza)} />
            )}
          </div>

          {/* PRODUZIONE */}
          <div className="border rounded-md p-3 space-y-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Produzione
            </div>

            {/* Materia prima — ricercabile e sovrascrivibile */}
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Materia prima</label>
              <MateriaPrimaCombobox
                value={effMp}
                onChange={setMpOverride}
                placeholder="Nessuna materia prima..."
              />
              {/* Warnings */}
              {effFlagNoMateria && (
                <p className="text-xs text-amber-600">⚠ materia prima non configurata</p>
              )}
              {effFlagLunghezzaMancante && (
                <p className="text-xs text-amber-600">⚠ lunghezza non configurata</p>
              )}
              {effMp && effLunghezzaMp && !mpOverride && (
                <p className="text-xs text-muted-foreground">
                  Lunghezza da {materiaPrimaCodice === effMp.codice && lunghezzaBarraDefault === lunghezzaEffettivaDefault
                    ? 'override articolo'
                    : 'materia prima'
                  }: {effLunghezzaMp} mm
                </p>
              )}
              {mpOverride && mpOverride.lunghezza_mm && (
                <p className="text-xs text-blue-600">
                  Override: {mpOverride.codice} · {mpOverride.lunghezza_mm} mm
                </p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Tipo produzione</label>
              <Select value={tipoProd} onValueChange={v => setTipoProd(v as TipoProduzione)}>
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIPO_PRODUZIONE_OPTIONS.map(t => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <NumInput label="Multipli taglio" value={multipliTaglio} onChange={setMultipliTaglio} />
              <NumInput label="mm materiale" value={mmMateriale} onChange={setMmMateriale}
                disabled={!['BARRA', 'FASCI'].includes(tipoProd)} />
            </div>
            {['BARRA', 'FASCI'].includes(tipoProd) && (
              <NumInput label="Lunghezza barra (mm)" value={lunghezzaBarra} onChange={setLunghezzaBarra} />
            )}

            {/* Lotti */}
            <div className="border-t pt-2 mt-1">
              <div className="flex items-center gap-2">
                <div className="space-y-0.5">
                  <label className="text-xs text-muted-foreground">Nr lotti</label>
                  <input
                    type="number"
                    min={0}
                    value={nrLottiOverride !== '' ? nrLottiOverride : calcolato.nrLotti}
                    onChange={e => setNrLottiOverride(e.target.value)}
                    className="flex h-8 w-20 rounded-md border border-input bg-transparent px-2 text-sm"
                  />
                </div>
                <span className="text-muted-foreground text-sm mt-4">×</span>
                <div className="space-y-0.5">
                  <label className="text-xs text-muted-foreground">Pz/lotto</label>
                  <div className="h-8 flex items-center px-2 text-sm font-medium">
                    {pezziPerLotto}
                  </div>
                </div>
                <span className="text-muted-foreground text-sm mt-4">=</span>
                <div className="space-y-0.5">
                  <label className="text-xs text-muted-foreground">Qty totale</label>
                  <div className={`h-8 flex items-center px-2 text-sm font-bold rounded ${
                    supera ? 'text-red-600' : 'text-green-700'
                  }`}>
                    {formatQty(qtySuggerita)}
                    {supera && <span className="ml-1 text-xs">⚠ supera capienza</span>}
                  </div>
                </div>
              </div>
              {qtyTarget > 0 && (
                <div className="text-xs text-muted-foreground mt-1">
                  Target: {formatQty(qtyTarget)} pz
                  {qtySuggerita !== qtyTarget && (
                    <span className="ml-1">
                      (arrotondato a lotto intero: +{qtySuggerita - qtyTarget} pz)
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── TABELLE IMPEGNI + PRODUZIONI ──────────────────────────── */}
        {dettaglioLoading ? (
          <div className="text-xs text-muted-foreground py-2">Caricamento dettagli...</div>
        ) : (
          <div className="grid grid-cols-2 gap-4 mt-2">

            {/* Impegni */}
            <div className="border rounded-md">
              <div className="px-3 py-1.5 bg-amber-50/70 text-xs font-semibold uppercase tracking-wide border-b">
                Impegni ({dettaglio?.impegni.length ?? 0})
              </div>
              {!dettaglio?.impegni.length ? (
                <div className="px-3 py-2 text-xs text-muted-foreground">Nessun impegno</div>
              ) : (
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="text-left px-3 py-1">Ordine</th>
                      <th className="text-left px-3 py-1">Cliente</th>
                      <th className="text-left px-3 py-1">Consegna</th>
                      <th className="text-right px-3 py-1">Qty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dettaglio.impegni.map(imp => (
                      <tr key={imp.riga_id} className="border-b last:border-0 hover:bg-muted/20">
                        <td className="px-3 py-1 font-mono">{imp.numero_ordine}</td>
                        <td className="px-3 py-1 truncate max-w-[80px]">{imp.cliente}</td>
                        <td className="px-3 py-1">{fmtData(imp.data_consegna)}</td>
                        <td className="px-3 py-1 text-right font-medium">{formatQty(imp.qty_da_evadere)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Produzioni attive */}
            <div className="border rounded-md">
              <div className="px-3 py-1.5 bg-slate-50 text-xs font-semibold uppercase tracking-wide border-b">
                Produzioni attive ({dettaglio?.produzioni_attive.length ?? 0})
              </div>
              {!dettaglio?.produzioni_attive.length ? (
                <div className="px-3 py-2 text-xs text-muted-foreground">Nessuna produzione</div>
              ) : (
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="text-left px-3 py-1">Stato</th>
                      <th className="text-right px-3 py-1">Qt cliente</th>
                      <th className="text-right px-3 py-1">Qt scorta</th>
                      <th className="text-left px-3 py-1">Data</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dettaglio.produzioni_attive.map(p => (
                      <tr key={p.commessa_id} className="border-b last:border-0 hover:bg-muted/20">
                        <td className="px-3 py-1">
                          <Badge variant="secondary" className="text-xs">{p.stato}</Badge>
                        </td>
                        <td className="px-3 py-1 text-right">{formatQty(p.qty_cliente)}</td>
                        <td className="px-3 py-1 text-right">{formatQty(p.qty_scorta)}</td>
                        <td className="px-3 py-1">{fmtData(p.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose}>Annulla</Button>
          {onLanciaSubito && (
            <Button
              variant="secondary"
              onClick={() => { onLanciaSubito(qtySuggerita); onClose() }}
              disabled={qtySuggerita <= 0}
            >
              Lancia subito
            </Button>
          )}
          <Button
            onClick={() => { onConferma(qtySuggerita); onClose() }}
            disabled={qtySuggerita <= 0}
          >
            {isModificato ? '✓ Conferma override' : 'Conferma'}
            {qtySuggerita > 0 && <span className="ml-1 opacity-70">({formatQty(qtySuggerita)} pz)</span>}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function Row({
  label, value, highlight = false,
}: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between items-baseline text-sm">
      <span className="text-muted-foreground text-xs">{label}</span>
      <span className={`font-medium tabular-nums ${highlight ? 'text-red-600' : ''}`}>{value}</span>
    </div>
  )
}

function NumInput({
  label, value, onChange, disabled = false,
}: { label: string; value: string; onChange: (v: string) => void; disabled?: boolean }) {
  return (
    <div className="space-y-0.5">
      <label className="text-xs text-muted-foreground">{label}</label>
      <input
        type="number"
        min={1}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder="—"
        disabled={disabled}
        className="flex h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm disabled:opacity-40"
      />
    </div>
  )
}
