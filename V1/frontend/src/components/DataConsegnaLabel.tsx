import { format, isPast, isWithinInterval, addDays } from 'date-fns'
import { it } from 'date-fns/locale'
import { cn } from '@/lib/utils'

interface Props {
  data: string | null
  flagScaduta?: boolean
  className?: string
}

export function DataConsegnaLabel({ data, flagScaduta, className }: Props) {
  if (!data) return <span className={cn('text-muted-foreground', className)}>—</span>

  const date = new Date(data)
  const scaduta = flagScaduta ?? isPast(date)
  const imminente = !scaduta && isWithinInterval(date, { start: new Date(), end: addDays(new Date(), 3) })

  return (
    <span className={cn(
      scaduta ? 'text-red-600 font-semibold' :
      imminente ? 'text-yellow-600 font-medium' :
      'text-foreground',
      className
    )}>
      {format(date, 'd MMM yyyy', { locale: it })}
      {scaduta && ' ⚠'}
    </span>
  )
}
