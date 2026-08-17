import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  DuplicateVisitConflict,
  fetchIntakeSchema,
  fetchMyPrefill,
  saveEncounter,
  saveMyEncounter,
  scoreSubmission,
} from '@/api/client'
import type {
  Assessment,
  Availability,
  FieldDef,
  FieldEntry,
  IntakePrefill,
  IntakeSchema,
  PatientProfile,
  SaveResult,
  Submission,
  VisitInfo,
} from '@/types'
import { FieldRenderer } from '@/components/intake/FieldRenderer'
import { ScorePreview } from '@/components/intake/ScorePreview'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AlertTriangle, CheckCircle2, Loader2, Save } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const VISIT_TAB = 'visit'
const SAVE_TAB = 'save'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function initialVisit(fields: FieldDef[], reviewer: string): VisitInfo {
  const byKey = Object.fromEntries(fields.map((f) => [f.key, f]))
  const str = (k: string) => String(byKey[k]?.default ?? '')
  return {
    patient_id: str('patient_id'),
    visit_id: str('visit_id'),
    visit_date: today(),
    age: Number(byKey.age?.default ?? 54),
    biological_sex: str('biological_sex'),
    region_profile: str('region_profile'),
    clinical_setting: str('clinical_setting'),
    // The signed-in account, not the schema's generic placeholder. Left blank
    // the API stamps the account anyway; prefilling just makes what will be
    // recorded visible, and still editable when someone else did the review.
    reviewed_by: reviewer,
  }
}

function initialPatientProfile(): PatientProfile {
  return {
    name: '',
    contact: {
      email: '',
      phone: '',
    },
    notification_preferences: {
      email: true,
      push: true,
    },
    emergency_contact: {
      name: '',
      relation: '',
      contact: {
        email: '',
        phone: '',
      },
    },
  }
}

export function IntakePage() {
  const [schema, setSchema] = useState<IntakeSchema | null>(null)
  const [schemaErr, setSchemaErr] = useState<string | null>(null)

  const { user } = useAuth()
  const reviewer = user?.name || user?.email || ''

  // A patient records their own visit: the server owns the patient id and the
  // visit id, so those inputs are hidden rather than shown and ignored.
  const selfMode = user?.role === 'patient'
  const [prefill, setPrefill] = useState<IntakePrefill | null>(null)

  const [visit, setVisit] = useState<VisitInfo | null>(null)
  const [patientProfile, setPatientProfile] = useState<PatientProfile>(initialPatientProfile)
  const [entries, setEntries] = useState<Record<string, FieldEntry>>({})
  const [lpaUnit, setLpaUnit] = useState('mg/dL')
  const [note, setNote] = useState('')
  const [tab, setTab] = useState(VISIT_TAB)

  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [scoring, setScoring] = useState(false)
  const [scoreErr, setScoreErr] = useState<string | null>(null)

  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState<SaveResult | null>(null)
  const [saveErr, setSaveErr] = useState<string | null>(null)
  const [duplicate, setDuplicate] = useState<string | null>(null)

  useEffect(() => {
    let stale = false

    // A returning patient starts from their last submission rather than a blank
    // 48-field form. The prefill arrives with every measurement age already
    // advanced, so reused values keep their real staleness.
    const loadPrefill = selfMode
      ? fetchMyPrefill().catch(() => null)
      : Promise.resolve(null)

    Promise.all([fetchIntakeSchema(), loadPrefill])
      .then(([s, previous]) => {
        if (stale) return
        setSchema(s)
        setNote(s.clinician_note_default)
        setPrefill(previous)

        const base = initialVisit(s.visit_fields, reviewer)
        if (previous) {
          setVisit({ ...base, ...previous.visit, visit_date: today() })
          setEntries(previous.fields)
          setLpaUnit(previous.lpa_unit)
        } else {
          setVisit(base)
        }
      })
      .catch((e) => {
        if (!stale) setSchemaErr(String(e))
      })

    return () => {
      stale = true
    }
  }, [reviewer, selfMode])

  const submission: Submission | null = useMemo(() => {
    if (!visit) return null
    return {
      visit,
      patient_profile: patientProfile,
      fields: entries,
      clinician_note: note,
      lpa_unit: lpaUnit,
    }
  }, [visit, patientProfile, entries, note, lpaUnit])

  // Debounced live scoring. The engine is cheap and deterministic, so
  // re-scoring on edit is the same work the Streamlit rerun did.
  const seq = useRef(0)
  useEffect(() => {
    if (!submission) return
    const mine = ++seq.current
    setScoring(true)
    const timer = setTimeout(() => {
      scoreSubmission(submission)
        .then((a) => {
          if (seq.current === mine) {
            setAssessment(a)
            setScoreErr(null)
          }
        })
        .catch((e) => {
          if (seq.current === mine) setScoreErr(String(e))
        })
        .finally(() => {
          if (seq.current === mine) setScoring(false)
        })
    }, 350)
    return () => clearTimeout(timer)
  }, [submission])

  const patchField = useCallback((key: string, patch: FieldEntry) => {
    setEntries((prev) => ({ ...prev, [key]: patch }))
    setSaved(null)
    setDuplicate(null)
  }, [])

  const patchVisit = useCallback((patch: Partial<VisitInfo>) => {
    setVisit((prev) => (prev ? { ...prev, ...patch } : prev))
    setSaved(null)
    setDuplicate(null)
  }, [])

  const patchPatientProfile = useCallback((patch: Partial<PatientProfile>) => {
    setPatientProfile((prev) => ({ ...prev, ...patch }))
    setSaved(null)
    setDuplicate(null)
  }, [])

  const doSave = async (allowDuplicate = false) => {
    if (!submission) return
    setSaving(true)
    setSaveErr(null)
    setDuplicate(null)
    try {
      // A patient posts to /me/encounters, where the server assigns both the
      // patient id and the visit id — so there is no duplicate visit to resolve.
      const result = selfMode
        ? await saveMyEncounter(submission)
        : await saveEncounter({
            ...submission,
            allow_duplicate_visit: allowDuplicate,
          })
      setSaved(result)
    } catch (e) {
      if (e instanceof DuplicateVisitConflict) {
        setDuplicate(e.info.message)
      } else {
        setSaveErr(String(e))
      }
    } finally {
      setSaving(false)
    }
  }

  if (schemaErr) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
        Could not load the form schema: {schemaErr}
      </div>
    )
  }

  if (!schema || !visit) {
    return (
      <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading form…
      </div>
    )
  }

  const visitByKey = Object.fromEntries(schema.visit_fields.map((f) => [f.key, f]))

  return (
    <div className="flex flex-col xl:flex-row gap-5 items-start">
      <div className="flex-1 min-w-0 w-full">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="flex-wrap h-auto">
            <TabsTrigger value={VISIT_TAB}>Patient &amp; Visit</TabsTrigger>
            {schema.tabs.map((t) => (
              <TabsTrigger key={t.id} value={t.id}>
                {t.title}
              </TabsTrigger>
            ))}
            <TabsTrigger value={SAVE_TAB}>Save Assessment</TabsTrigger>
          </TabsList>

          {/* Patient & visit metadata */}
          <TabsContent value={VISIT_TAB} className="mt-4">
            {selfMode && prefill && (
              <div className="mb-4 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm">
                <p className="font-medium">Continuing from your last visit</p>
                <p className="text-muted-foreground mt-0.5 leading-relaxed">
                  Your previous answers are filled in, and each measurement is
                  now recorded as {prefill.months_since_last_visit} months older.
                  Update anything that has changed — especially any test you have
                  had redone, so its date is right.
                </p>
              </div>
            )}

            <div className="rounded-xl border bg-card shadow-xs p-4">
              <h3 className="text-sm font-semibold mb-1">
                {selfMode ? 'About you' : 'Patient and visit details'}
              </h3>
              <p className="text-xs text-muted-foreground mb-4">
                {selfMode
                  ? 'Your details for this visit. Everything is saved against your own record.'
                  : 'Core administrative and demographic fields for the active encounter.'}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Hidden in self mode: the server assigns both ids, so showing
                    an input that is silently ignored would be a lie. */}
                {!selfMode && (
                  <div>
                    <Label className="text-xs mb-1 block">
                      {visitByKey.patient_id.label}
                    </Label>
                    <Input
                      value={visit.patient_id}
                      onChange={(e) => patchVisit({ patient_id: e.target.value })}
                      className="h-8"
                    />
                  </div>
                )}
                {!selfMode && (
                  <div>
                    <Label className="text-xs mb-1 block">
                      {visitByKey.visit_id.label}
                    </Label>
                    <Input
                      value={visit.visit_id}
                      onChange={(e) => patchVisit({ visit_id: e.target.value })}
                      className="h-8"
                    />
                  </div>
                )}
                <div>
                  <Label className="text-xs mb-1 block">
                    {visitByKey.visit_date.label}
                  </Label>
                  <Input
                    type="date"
                    value={visit.visit_date}
                    onChange={(e) => patchVisit({ visit_date: e.target.value })}
                    className="h-8"
                  />
                </div>
                <div>
                  <Label className="text-xs mb-1 block">{visitByKey.age.label}</Label>
                  <Input
                    type="number"
                    min={visitByKey.age.min}
                    max={visitByKey.age.max}
                    step={visitByKey.age.step}
                    value={visit.age}
                    onChange={(e) => patchVisit({ age: Number(e.target.value) })}
                    className="h-8"
                  />
                </div>

                {(['biological_sex', 'region_profile', 'clinical_setting'] as const).map(
                  (key) => (
                    <div key={key}>
                      <Label className="text-xs mb-1 block">{visitByKey[key].label}</Label>
                      <Select
                        value={visit[key]}
                        onValueChange={(v) => patchVisit({ [key]: v } as Partial<VisitInfo>)}
                      >
                        <SelectTrigger className="h-8! text-xs w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {(visitByKey[key].options ?? []).map((o) => (
                            <SelectItem key={o} value={o}>
                              {o}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ),
                )}

                {/* Self-recorded visits are stamped "Self-reported" server-side
                    so a clinician can tell them from a reviewed encounter. */}
                {!selfMode && (
                  <div>
                    <Label className="text-xs mb-1 block">
                      {visitByKey.reviewed_by.label}
                    </Label>
                    <Input
                      value={visit.reviewed_by}
                      onChange={(e) => patchVisit({ reviewed_by: e.target.value })}
                      className="h-8"
                    />
                  </div>
                )}
              </div>

              <div className="mt-5 border-t pt-5">
                <h3 className="text-sm font-semibold mb-1">Patient details</h3>
                <p className="text-xs text-muted-foreground mb-4">
                  Stored on the patient profile for monitoring and notifications.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <Label className="text-xs mb-1 block">Full Name</Label>
                    <Input
                      value={patientProfile.name}
                      onChange={(e) => patchPatientProfile({ name: e.target.value })}
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs mb-1 block">Email Address</Label>
                    <Input
                      type="email"
                      value={patientProfile.contact.email}
                      onChange={(e) =>
                        patchPatientProfile({
                          contact: {
                            ...patientProfile.contact,
                            email: e.target.value,
                          },
                        })
                      }
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs mb-1 block">Phone Number</Label>
                    <Input
                      value={patientProfile.contact.phone}
                      onChange={(e) =>
                        patchPatientProfile({
                          contact: {
                            ...patientProfile.contact,
                            phone: e.target.value,
                          },
                        })
                      }
                      className="h-8"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-5 border-t pt-5">
                <h3 className="text-sm font-semibold mb-1">Emergency contact</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
                  <div>
                    <Label className="text-xs mb-1 block">Name</Label>
                    <Input
                      value={patientProfile.emergency_contact.name}
                      onChange={(e) =>
                        patchPatientProfile({
                          emergency_contact: {
                            ...patientProfile.emergency_contact,
                            name: e.target.value,
                          },
                        })
                      }
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs mb-1 block">Relationship</Label>
                    <Input
                      value={patientProfile.emergency_contact.relation}
                      onChange={(e) =>
                        patchPatientProfile({
                          emergency_contact: {
                            ...patientProfile.emergency_contact,
                            relation: e.target.value,
                          },
                        })
                      }
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs mb-1 block">Phone Number</Label>
                    <Input
                      value={patientProfile.emergency_contact.contact.phone}
                      onChange={(e) =>
                        patchPatientProfile({
                          emergency_contact: {
                            ...patientProfile.emergency_contact,
                            contact: {
                              ...patientProfile.emergency_contact.contact,
                              phone: e.target.value,
                            },
                          },
                        })
                      }
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs mb-1 block">Email Address</Label>
                    <Input
                      type="email"
                      value={patientProfile.emergency_contact.contact.email}
                      onChange={(e) =>
                        patchPatientProfile({
                          emergency_contact: {
                            ...patientProfile.emergency_contact,
                            contact: {
                              ...patientProfile.emergency_contact.contact,
                              email: e.target.value,
                            },
                          },
                        })
                      }
                      className="h-8"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-5 border-t pt-5">
                <h3 className="text-sm font-semibold mb-1">Notification preferences</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                  <div>
                    <Label className="text-xs mb-1 block">
                      Receive Email Notifications
                    </Label>
                    <Select
                      value={patientProfile.notification_preferences.email ? 'Yes' : 'No'}
                      onValueChange={(v) =>
                        patchPatientProfile({
                          notification_preferences: {
                            ...patientProfile.notification_preferences,
                            email: v === 'Yes',
                          },
                        })
                      }
                    >
                      <SelectTrigger className="h-8! text-xs w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Yes">Yes</SelectItem>
                        <SelectItem value="No">No</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs mb-1 block">
                      Receive Push Notifications
                    </Label>
                    <Select
                      value={patientProfile.notification_preferences.push ? 'Yes' : 'No'}
                      onValueChange={(v) =>
                        patchPatientProfile({
                          notification_preferences: {
                            ...patientProfile.notification_preferences,
                            push: v === 'Yes',
                          },
                        })
                      }
                    >
                      <SelectTrigger className="h-8! text-xs w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Yes">Yes</SelectItem>
                        <SelectItem value="No">No</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <p className="text-xs text-muted-foreground mt-4">{schema.visit_note}</p>
            </div>
          </TabsContent>

          {/* Scored input feeds, one tab per schema tab */}
          {schema.tabs.map((t) => (
            <TabsContent key={t.id} value={t.id} className="mt-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
                {t.columns.map((column, ci) => (
                  <div key={ci} className="space-y-4">
                    {column.map((section) => (
                      <div
                        key={section.section}
                        className="rounded-xl border bg-card shadow-xs p-4"
                      >
                        <h3 className="text-sm font-semibold mb-3">{section.section}</h3>
                        {section.groups.map((group) => (
                          <div
                            key={group.title}
                            className="rounded-lg border bg-background/50 p-3 mb-3 last:mb-0"
                          >
                            <div className="text-xs font-semibold mb-0.5">
                              {group.title}
                            </div>
                            {group.note && (
                              <p className="text-[11px] text-muted-foreground mb-2 leading-snug">
                                {group.note}
                              </p>
                            )}
                            {group.fields.map((field) =>
                              field.widget === 'lpa_unit' ? (
                                <div
                                  key={field.key}
                                  className="flex items-center justify-between gap-3 py-2.5 border-b border-border/40"
                                >
                                  <Label className="text-sm font-medium">
                                    {field.label}
                                  </Label>
                                  <Select
                                    value={lpaUnit}
                                    onValueChange={(v) => setLpaUnit(String(v))}
                                  >
                                    <SelectTrigger className="w-32 h-8! text-xs shrink-0">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {(field.options ?? []).map((o) => (
                                        <SelectItem key={o} value={o}>
                                          {o}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </div>
                              ) : (
                                <FieldRenderer
                                  key={field.key}
                                  field={field}
                                  entry={entries[field.key] ?? {}}
                                  availabilityOptions={
                                    schema.availability_options as Availability[]
                                  }
                                  unitOverride={
                                    field.key === 'lpa' ? lpaUnit : undefined
                                  }
                                  onChange={(patch) => patchField(field.key, patch)}
                                />
                              ),
                            )}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                ))}
              </div>

              {t.id === 'treatment' && (
                <div className="rounded-xl border bg-card shadow-xs p-4 mt-4">
                  <h3 className="text-sm font-semibold mb-2">Clinician note</h3>
                  <Textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    rows={4}
                    className="text-sm"
                  />
                </div>
              )}
            </TabsContent>
          ))}

          {/* Save */}
          <TabsContent value={SAVE_TAB} className="mt-4">
            <div className="rounded-xl border bg-card shadow-xs p-4 space-y-4">
              <div>
                <h3 className="text-sm font-semibold mb-1">Save assessment</h3>
                <p className="text-xs text-muted-foreground">
                  Writes this encounter to MongoDB, where the dashboard reads it from
                  the <code className="text-[11px]">payload</code> source.
                </p>
              </div>

              <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <div>
                  <dt className="text-xs text-muted-foreground">Patient</dt>
                  <dd className="font-medium">
                    {selfMode ? 'You' : visit.patient_id || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Visit</dt>
                  <dd className="font-medium">
                    {selfMode ? 'Assigned on save' : visit.visit_id || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Date</dt>
                  <dd className="font-medium tabular-nums">{visit.visit_date}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Score</dt>
                  <dd className="font-medium tabular-nums">
                    {assessment ? assessment.hhs : '—'}
                  </dd>
                </div>
              </dl>

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  onClick={() => doSave(false)}
                  disabled={saving || (!selfMode && (!visit.patient_id || !visit.visit_id))}
                >
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" /> Saving…
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      {selfMode ? 'Save my visit' : 'Save Assessment'}
                    </>
                  )}
                </Button>
                {!selfMode && (!visit.patient_id || !visit.visit_id) && (
                  <span className="text-xs text-muted-foreground">
                    Patient ID and Visit ID are required.
                  </span>
                )}
              </div>

              {duplicate && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-3">
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-amber-700 dark:text-amber-400 mb-1">
                    <AlertTriangle className="h-4 w-4" /> Duplicate visit
                  </div>
                  <p className="text-xs text-amber-700/90 dark:text-amber-300/90 mb-2">
                    {duplicate}
                  </p>
                  <Button size="sm" variant="outline" onClick={() => doSave(true)}>
                    Save anyway
                  </Button>
                </div>
              )}

              {saveErr && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  {saveErr}
                </div>
              )}

              {saved && (
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-3 py-3">
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-400 mb-1.5">
                    <CheckCircle2 className="h-4 w-4" />
                    {selfMode ? 'Visit saved' : 'Assessment saved'}
                  </div>

                  {selfMode ? (
                    <>
                      <p className="text-sm">
                        Your Heart Health Score is{' '}
                        <span className="font-semibold tabular-nums">
                          {saved.assessment.hhs}
                        </span>
                        .
                      </p>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        Recorded as {saved.visit_id}. Record another visit later
                        to see how it changes over time — a trend needs at least
                        two.
                      </p>
                      <Link
                        to="/my-health"
                        className={cn(buttonVariants({ size: 'sm' }), 'mt-3')}
                      >
                        See my full result
                      </Link>
                    </>
                  ) : (
                    <>
                      <div className="text-xs text-muted-foreground space-y-0.5">
                        <div>Patient ID: {saved.patient_id}</div>
                        <div>Visit ID: {saved.visit_id}</div>
                        <div>Encounter ID: {saved.encounter_id}</div>
                        <div>Timestamp: {saved.timestamp}</div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">
                        Available for review under the MongoDB payload source.
                      </p>
                    </>
                  )}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <aside className="w-full xl:w-80 shrink-0 xl:sticky xl:top-[77px]">
        <ScorePreview assessment={assessment} scoring={scoring} error={scoreErr} />
      </aside>
    </div>
  )
}
