import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format } from 'date-fns'
import { it } from 'date-fns/locale'

// ─── Tailwind class merger ─────────────────────────────────────────────────────

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ─── Formattazione ────────────────────────────────────────────────────────────

export function formatData(isoString: string | null): string {
  if (!isoString) return '—'
  return format(new Date(isoString), 'd MMM yyyy', { locale: it })
}

export function formatDataOra(isoString: string | null): string {
  if (!isoString) return '—'
  return format(new Date(isoString), 'd MMM yyyy HH:mm', { locale: it })
}

export function formatQty(n: number): string {
  return n.toLocaleString('it-IT')
}

export function formatPeso(kg: number | null): string {
  if (kg === null) return '—'
  return `${kg.toLocaleString('it-IT')} kg`
}

// ─── Estrazione errore API ────────────────────────────────────────────────────

export function extractApiError(err: unknown): string {
  if (
    err &&
    typeof err === 'object' &&
    'response' in err &&
    err.response &&
    typeof err.response === 'object' &&
    'data' in err.response &&
    err.response.data &&
    typeof err.response.data === 'object' &&
    'detail' in err.response.data
  ) {
    return String((err.response.data as { detail: string }).detail)
  }
  return 'Errore imprevisto — riprovare'
}

// ─── Download Excel ────────────────────────────────────────────────────────────

export function downloadExcel(base64: string, filename: string) {
  const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0))
  const blob = new Blob([bytes], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
