interface Props {
  cliente: string | null
  className?: string
}

export function ClienteLabel({ cliente, className }: Props) {
  return (
    <span className={className}>
      {cliente ?? '—'}
    </span>
  )
}
