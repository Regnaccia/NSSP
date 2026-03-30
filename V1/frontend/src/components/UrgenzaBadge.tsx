import { Badge } from '@/components/ui/badge'

interface Props {
  attiva: boolean
  className?: string
}

export function UrgenzaBadge({ attiva, className }: Props) {
  if (!attiva) return null
  return (
    <Badge variant="destructive" className={className}>
      URGENTE
    </Badge>
  )
}
