// Shared date formatting for the trend charts. The backend sends ISO-8601 UTC.

export function formatAxisDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function formatFullDate(value: unknown): string {
  const date = new Date(String(value))
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}
