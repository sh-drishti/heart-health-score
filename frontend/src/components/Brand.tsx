import drishtiLogo from '@/assets/drishti-logo.svg'
import drishtiEye from '@/assets/drishti-eye.svg'
import heartIcon from '@/assets/hhs-heart.png'
import { cn } from '@/lib/utils'

export const APP_NAME = 'Heart Health Score'
export const TAGLINE = 'Your premium health companion'

const FOUNDATION = 'IITI Drishti CPS Foundation, IIT Indore'

/**
 * The foundation's logo, a divider, then the app's own mark and name.
 *
 * Narrow screens keep both marks but drop text: the foundation logo shrinks to
 * its eye (the same artwork, cropped), and the app name and tagline go below
 * `sm`.
 *
 * The foundation logo has black and navy lettering that disappears on a dark
 * background, so in dark mode it sits on a white plate rather than being
 * recoloured.
 */
export function Brand({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-3 min-w-0', className)}>
      <span className="shrink-0 dark:rounded-md dark:bg-white dark:px-1.5 dark:py-0.5">
        <img src={drishtiEye} alt={FOUNDATION} className="h-9 w-auto md:hidden" />
        <img src={drishtiLogo} alt={FOUNDATION} className="hidden md:block h-9 w-auto" />
      </span>

      <span aria-hidden className="h-8 w-px shrink-0 bg-border" />

      <div className="flex items-center gap-2.5 min-w-0">
        <img src={heartIcon} alt="" className="h-10 w-10 shrink-0" />
        <div className="hidden sm:block min-w-0">
          <h1 className="font-heading text-base font-semibold leading-tight truncate">
            {APP_NAME}
          </h1>
          <p className="text-xs text-muted-foreground leading-tight truncate">{TAGLINE}</p>
        </div>
      </div>
    </div>
  )
}
