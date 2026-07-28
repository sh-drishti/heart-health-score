import type { Availability, FieldDef, FieldEntry } from '@/types'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

interface Props {
  field: FieldDef
  entry: FieldEntry
  availabilityOptions: Availability[]
  /** Overrides the schema unit for Lp(a), whose unit is chosen by a select. */
  unitOverride?: string
  onChange: (patch: FieldEntry) => void
}

// Availability + value + months-old, matching number_input_field in the
// Streamlit form: a non-Available status hides the value entirely rather than
// storing a zero, because the engine treats missing and normal differently.
function NumberField({
  field,
  entry,
  availabilityOptions,
  unitOverride,
  onChange,
  slider,
}: Props & { slider?: boolean }) {
  const status = entry.status ?? field.default_status ?? 'Available'
  const unit = unitOverride ?? field.unit ?? ''
  const value = entry.value ?? field.default ?? 0
  const months = entry.months_old ?? field.months_default ?? 0

  return (
    <div className="py-2.5 border-b border-border/40 last:border-0">
      <div className="flex items-start justify-between gap-3 mb-1.5">
        <Label className="text-sm font-medium leading-snug">
          {field.label}
          {unit && <span className="text-muted-foreground font-normal"> ({unit})</span>}
        </Label>
        <Select
          value={status}
          onValueChange={(v) => onChange({ ...entry, status: v as Availability })}
        >
          <SelectTrigger className="w-36 h-7! text-xs shrink-0">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {availabilityOptions.map((o) => (
              <SelectItem key={o} value={o}>
                {o}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {status === 'Available' && (
        <div className="flex items-end gap-3">
          <div className="flex-1 min-w-0">
            {slider ? (
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={field.min}
                  max={field.max}
                  step={field.step}
                  value={Number(value)}
                  onChange={(e) => onChange({ ...entry, value: Number(e.target.value) })}
                  className="flex-1 accent-primary cursor-pointer"
                />
                <span className="text-sm font-semibold tabular-nums w-10 text-right">
                  {Number(value)}
                </span>
              </div>
            ) : (
              <Input
                type="number"
                min={field.min}
                max={field.max}
                step={field.step}
                value={Number(value)}
                onChange={(e) => onChange({ ...entry, value: Number(e.target.value) })}
                className="h-8"
              />
            )}
          </div>
          <div className="w-28 shrink-0">
            <Label className="text-[11px] text-muted-foreground mb-1 block">
              Months old
            </Label>
            <Input
              type="number"
              min={0}
              max={field.months_max ?? 240}
              step={1}
              value={Number(months)}
              onChange={(e) => onChange({ ...entry, months_old: Number(e.target.value) })}
              className="h-8"
            />
          </div>
        </div>
      )}
    </div>
  )
}

// Categorical and yes/no share a shape: "Unknown" implies status Unknown,
// which the backend applies when building the FieldRecord.
function ChoiceField({ field, entry, onChange }: Props) {
  const value = String(entry.value ?? field.default ?? 'Unknown')
  const options = field.options ?? []
  const isUnknown = value === 'Unknown'

  return (
    <div className="flex items-center justify-between gap-3 py-2.5 border-b border-border/40 last:border-0">
      <Label className="text-sm font-medium leading-snug">{field.label}</Label>
      <Select value={value} onValueChange={(v) => onChange({ ...entry, value: v })}>
        <SelectTrigger
          className={cn('w-44 h-8! text-xs shrink-0', isUnknown && 'text-muted-foreground')}
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export function FieldRenderer(props: Props) {
  const { field } = props

  switch (field.widget) {
    case 'number':
      return <NumberField {...props} />
    case 'slider':
      return <NumberField {...props} slider />
    case 'select':
    case 'yes_no':
      return <ChoiceField {...props} />
    default:
      return null
  }
}
