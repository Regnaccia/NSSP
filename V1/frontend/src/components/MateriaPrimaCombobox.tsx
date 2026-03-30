/**
 * Combobox per selezione/ricerca materia prima.
 * Usato in LancioModal (override sessione) e in Articoli (salvataggio permanente).
 */
import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'

import { officeClient } from '@/api/officeClient'
import type { MateriaPrimaResponse } from '@/types/api'

export type MateriaPrimaOption = {
  id: string
  codice: string
  descrizione: string | null
  lunghezza_mm: number | null
}

type Props = {
  value: MateriaPrimaOption | null
  onChange: (mp: MateriaPrimaOption | null) => void
  placeholder?: string
  className?: string
}

export default function MateriaPrimaCombobox({ value, onChange, placeholder, className }: Props) {
  const [query, setQuery] = useState(value?.codice ?? '')
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Query di ricerca — si attiva quando il dropdown è aperto e c'è almeno 1 char
  const { data: results } = useQuery({
    queryKey: ['materie-prime-search', query],
    queryFn: () =>
      officeClient
        .get<MateriaPrimaResponse[]>('/api/materie-prime', { params: { q: query } })
        .then(r => r.data),
    enabled: open && query.length >= 1,
    staleTime: 30_000,
  })

  // Chiude il dropdown al click esterno, ripristina l'input al codice corrente
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
        setQuery(value?.codice ?? '')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [value])

  // Sincronizza query quando il valore cambia dall'esterno
  useEffect(() => {
    setQuery(value?.codice ?? '')
  }, [value?.id])

  const handleSelect = (mp: MateriaPrimaResponse) => {
    onChange({ id: mp.id, codice: mp.codice, descrizione: mp.descrizione, lunghezza_mm: mp.lunghezza_mm })
    setQuery(mp.codice)
    setOpen(false)
  }

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(null)
    setQuery('')
  }

  return (
    <div ref={containerRef} className={`relative ${className ?? ''}`}>
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={e => { setQuery(e.target.value.toUpperCase()); setOpen(true) }}
          onFocus={() => setOpen(true)}
          placeholder={placeholder ?? 'Cerca materia prima...'}
          className="flex h-8 w-full rounded-md border border-input bg-transparent px-2 pr-6 text-sm font-mono"
          autoComplete="off"
        />
        {value && (
          <button
            onMouseDown={handleClear}
            className="absolute right-1.5 top-1.5 text-muted-foreground hover:text-foreground leading-none"
            tabIndex={-1}
            title="Rimuovi"
          >
            ×
          </button>
        )}
      </div>

      {open && results && results.length > 0 && (
        <div className="absolute top-9 left-0 right-0 z-50 bg-background border rounded-md shadow-lg max-h-52 overflow-y-auto">
          {results.map(mp => (
            <button
              key={mp.id}
              onMouseDown={() => handleSelect(mp)}
              className="flex items-center justify-between w-full px-3 py-1.5 text-sm hover:bg-muted text-left gap-3"
            >
              <span className="font-mono font-medium shrink-0">{mp.codice}</span>
              <span className="text-muted-foreground text-xs truncate flex-1 text-left">
                {mp.descrizione}
              </span>
              {mp.lunghezza_mm != null
                ? <span className="text-xs text-muted-foreground shrink-0">{mp.lunghezza_mm} mm</span>
                : <span className="text-xs text-amber-500 shrink-0">⚠ no mm</span>
              }
            </button>
          ))}
        </div>
      )}

      {open && query.length >= 1 && results?.length === 0 && (
        <div className="absolute top-9 left-0 right-0 z-50 bg-background border rounded-md shadow-lg px-3 py-2 text-xs text-muted-foreground">
          Nessuna materia prima trovata
        </div>
      )}
    </div>
  )
}
