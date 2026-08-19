import { useEffect, useState } from 'react'
import type { Assessment, SavedValidation } from '@/types'
import type { SeverityLevel } from '@/config/domains'
import { fetchValidation, saveValidation } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { SeverityDot } from './SeverityBadge'

interface Props {
  patientId: string
  assessment: Assessment
}

// Mirrors hhs_v1_2_ui_app.score_category thresholds exactly.
const SCORE_BANDS: { label: string; range: string; level: SeverityLevel }[] = [
  { label: 'Favorable', range: '80–100', level: 'ok' },
  { label: 'Mildly elevated', range: '65–79', level: 'warn' },
  { label: 'Moderate burden', range: '50–64', level: 'warn' },
  { label: 'High burden', range: '30–49', level: 'risk' },
  { label: 'Very high burden', range: '0–29', level: 'risk' },
]

export function ClinicalValidation({ patientId, assessment }: Props) {
  const [agreement, setAgreement] = useState<'Yes' | 'No'>('Yes')
  const [doctorHhs, setDoctorHhs] = useState<number>(assessment.hhs)
  const [reason, setReason] = useState('')
  const [existing, setExisting] = useState<SavedValidation | null>(null)
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  // Load what was recorded before, so the form shows the current state rather
  // than a blank slate that invites overwriting an earlier judgement unseen.
  useEffect(() => {
    let stale = false
    setExisting(null)
    setSaved(false)
    setErr(null)
    setAgreement('Yes')
    setDoctorHhs(assessment.hhs)
    setReason('')

    fetchValidation(patientId)
      .then((found) => {
        if (stale || !found) return
        setExisting(found)
        setAgreement(found.agreement === 'No' ? 'No' : 'Yes')
        setDoctorHhs(found.doctor_hhs ?? assessment.hhs)
        setReason(found.reason ?? '')
      })
      .catch(() => {
        /* Not worth blocking the form: the clinician can still record one. */
      })

    return () => {
      stale = true
    }
  }, [patientId, assessment.hhs])

  const save = async () => {
    setSaving(true)
    setSaved(false)
    setErr(null)
    try {
      const stored = await saveValidation(patientId, {
        agreement,
        calculated_hhs: assessment.hhs,
        doctor_hhs: agreement === 'Yes' ? assessment.hhs : doctorHhs,
        reason: agreement === 'Yes' ? '' : reason,
      })
      setExisting(stored)
      setSaved(true)
    } catch (e) {
      // Reported in the UI, not just the console: this used to claim success
      // while the record was being dropped, which is the failure that matters.
      setErr(e instanceof Error ? e.message : 'Could not save the assessment.')
    } finally {
      setSaving(false)
    }
  }

  // The engine's score moves as new encounters arrive, so a validation recorded
  // against an earlier score is worth pointing out rather than quietly showing
  // a stale doctor's figure next to a changed calculated one.
  const scoreMoved =
    existing != null &&
    existing.calculated_hhs != null &&
    existing.calculated_hhs !== assessment.hhs

  return (
    <div className="mt-8">
      <h3 className="text-lg font-semibold mb-4">Clinical Validation</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Assessment Review</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-8">
              <div>
                <div className="text-xs text-muted-foreground">Calculated HHS</div>
                <div className="text-2xl font-bold">{assessment.hhs}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Confidence</div>
                <div className="text-2xl font-bold">{assessment.confidence_label}</div>
              </div>
            </div>

            <div>
              <Label className="mb-2 block">
                Does the calculated Healthy Heart Score match your clinical assessment?
              </Label>
              <RadioGroup
                value={agreement}
                onValueChange={(v) => setAgreement(v as 'Yes' | 'No')}
                className="flex gap-4"
              >
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="Yes" id="agree-yes" />
                  <Label htmlFor="agree-yes">Yes</Label>
                </div>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="No" id="agree-no" />
                  <Label htmlFor="agree-no">No</Label>
                </div>
              </RadioGroup>
            </div>

            {agreement === 'No' && (
              <>
                <div>
                  <Label htmlFor="doctor-hhs" className="mb-1 block">
                    Doctor&apos;s Healthy Heart Score
                  </Label>
                  <Input
                    id="doctor-hhs"
                    type="number"
                    min={0}
                    max={100}
                    step={0.5}
                    value={doctorHhs}
                    onChange={(e) => setDoctorHhs(Number(e.target.value))}
                    className="w-32"
                  />
                </div>
                <div>
                  <Label htmlFor="reason" className="mb-1 block">
                    Reason (Optional)
                  </Label>
                  <Textarea
                    id="reason"
                    placeholder="Explain why you modified the calculated HHS..."
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={3}
                  />
                </div>
              </>
            )}

            <div className="flex items-center gap-3 flex-wrap">
              <Button onClick={save} disabled={saving}>
                {saving ? 'Saving…' : existing ? 'Update Assessment' : 'Save Assessment'}
              </Button>
              {saved && (
                <span className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                  Assessment saved.
                </span>
              )}
              {err && (
                <span className="text-sm text-destructive font-medium">{err}</span>
              )}
            </div>

            {existing && !saved && (
              <p className="text-xs text-muted-foreground border-t pt-3">
                Recorded by {existing.author || 'unknown'} on{' '}
                {new Date(existing.updated_at).toLocaleString()}
                {scoreMoved && (
                  <>
                    , against a calculated score of {existing.calculated_hhs}. The
                    engine now scores {assessment.hhs}.
                  </>
                )}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Healthy Heart Score Guide</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Category</TableHead>
                  <TableHead>Score</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {SCORE_BANDS.map((band) => (
                  <TableRow key={band.label}>
                    <TableCell>
                      <span className="inline-flex items-center gap-2">
                        <SeverityDot level={band.level} /> {band.label}
                      </span>
                    </TableCell>
                    <TableCell className="tabular-nums">{band.range}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}