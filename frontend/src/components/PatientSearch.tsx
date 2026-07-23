import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Props {
  onSearch: (patientId: string) => void
  error?: string | null
}

export function PatientSearch({ onSearch, error }: Props) {
  const [value, setValue] = useState('')

  return (
    <form
      className="flex flex-wrap items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        onSearch(value.trim())
      }}
    >
      <Input
        type="text"
        placeholder="e.g. SYN-0001"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="max-w-sm"
      />
      <Button type="submit">Go</Button>
      {error && <span className="text-destructive text-sm">{error}</span>}
    </form>
  )
}