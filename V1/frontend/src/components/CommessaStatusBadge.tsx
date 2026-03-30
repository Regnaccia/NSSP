import { Badge } from '@/components/ui/badge'
import type { StatoCommessa } from '@/types/api'

const CONFIG: Record<StatoCommessa, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  in_coda:       { label: 'In coda',       variant: 'secondary' },
  in_produzione: { label: 'In produzione', variant: 'default' },
  sospesa:       { label: 'Sospesa',       variant: 'destructive' },
  completata:    { label: 'Completata',    variant: 'outline' },
}

export function CommessaStatusBadge({ stato }: { stato: StatoCommessa }) {
  const { label, variant } = CONFIG[stato]
  return <Badge variant={variant}>{label}</Badge>
}
