// Shared date formatting for the trend charts. The backend sends ISO-8601 UTC.

export function formatAxisDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

/**
 * Axis formatter for a set of visit dates. Once the visits cross a year
 * boundary the year is shown too, or a year of visits would show two "Dec 8"s.
 */
export function axisDateFormatter(dates: string[]): (value: string) => string {
  const years = new Set(
    dates.map((d) => new Date(d).getFullYear()).filter((y) => !Number.isNaN(y)),
  )
  if (years.size <= 1) return formatAxisDate

  return (value: string) => {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return String(value)
    const yy = String(date.getFullYear()).slice(-2)
    return `${formatAxisDate(value)} '${yy}`
  }
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
