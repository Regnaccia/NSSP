import { Badge } from '@/components/ui/badge'
import type { StatoSpedizione } from '@/types/api'

const CONFIG: Record<StatoSpedizione, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
  in_preparazione: { label: 'In preparazione', variant: 'secondary' },
  spedita:         { label: 'Spedita',         variant: 'default' },
  annullata:       { label: 'Annullata',       variant: 'outline' },
}

export function SpedizioneStatusBadge({ stato }: { stato: StatoSpedizione }) {
  const { label, variant } = CONFIG[stato]
  return <Badge variant={variant}>{label}</Badge>
}
