// Pastel versions of the chart colours. Soft enough to read as a set, but each
// is kept dark enough to show as a 2.5px line on a white card; they get easier
// to read, not harder, on the dark theme.

/** Ten domains, so the five --chart-* tokens are not enough. */
export const DOMAIN_PASTELS = [
  '#6cc9b8', // teal
  '#9aa8f5', // indigo
  '#f2b866', // amber
  '#b9a3f2', // violet
  '#7fbfe6', // sky
  '#f19aab', // rose
  '#a6cf7a', // lime
  '#ee9fcb', // pink
  '#7fd1a0', // green
  '#a3afc0', // slate
]

export const HHS_PASTEL = '#6cc9b8'
export const CONFIDENCE_PASTEL = '#9aa8f5'

/** Show a dot per visit up to this many; past it the line alone reads better. */
export const MAX_DOTS = 20
