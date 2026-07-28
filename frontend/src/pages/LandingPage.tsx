import { Link } from 'react-router-dom'
import { ArrowRight, ClipboardPlus, HeartPulse, Stethoscope } from 'lucide-react'
import { ThemeToggle } from '@/components/ThemeToggle'

const VIEWS = [
  {
    to: '/dashboard',
    icon: Stethoscope,
    title: 'Clinical Dashboard',
    role: 'For reviewing clinicians',
    body: 'Review a scored patient: domain burden, severities, red flags, data confidence, and clinical validation.',
    action: 'Open dashboard',
  },
  {
    to: '/entry',
    icon: ClipboardPlus,
    title: 'Encounter Entry',
    role: 'For intake staff',
    body: 'Record a new encounter across 48 clinical inputs, see the score update live, and save it for review.',
    action: 'Start an encounter',
  },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b bg-card/80 backdrop-blur">
        <div className="max-w-[1100px] mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <HeartPulse className="h-4.5 w-4.5" />
            </span>
            <div>
              <h1 className="text-base font-semibold tracking-tight leading-tight">
                Healthy Heart Score
              </h1>
              <p className="text-xs text-muted-foreground leading-tight">HHS-v1.2</p>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-[1100px]">
          <div className="text-center mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Choose a workspace
            </h2>
            <p className="text-sm text-muted-foreground mt-2 max-w-xl mx-auto">
              Cardiovascular risk assessment on the HHS-v1.2 engine. Research
              prototype — not validated for clinical decision-making.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {VIEWS.map((view) => (
              <Link
                key={view.to}
                to={view.to}
                className="group rounded-2xl border bg-card p-6 shadow-xs transition-all hover:shadow-md hover:border-primary/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary mb-4">
                  <view.icon className="h-5.5 w-5.5" />
                </span>

                <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {view.role}
                </div>
                <h3 className="text-lg font-semibold tracking-tight mt-0.5">
                  {view.title}
                </h3>
                <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
                  {view.body}
                </p>

                <span className="inline-flex items-center gap-1.5 text-sm font-medium text-primary mt-5">
                  {view.action}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
