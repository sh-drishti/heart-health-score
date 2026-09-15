/**
 * Below are the colors that are used in the app. The colors are defined in the light and dark mode.
 * There are many other ways to style your app. For example, [Nativewind](https://www.nativewind.dev/), [Tamagui](https://tamagui.dev/), [unistyles](https://reactnativeunistyles.vercel.app), etc.
 */

import '@/global.css';

import { Platform } from 'react-native';

/**
 * Semantic tokens, not raw colours.
 *
 * Components ask for `border` or `risk`, never a hex literal — which is what
 * lets the two schemes stay coherent, and what stops a status colour drifting
 * apart across screens.
 *
 * The palette is deliberately restrained. This app shows someone a number about
 * their heart; a saturated interface would be working against the content. The
 * accent is a muted teal — clinical without being cold — and saturation is
 * reserved for the score bands, where colour actually carries meaning.
 */
export const Colors = {
  light: {
    text: '#11201F',
    textSecondary: '#5B6B69',
    background: '#F7F9F8',
    backgroundElement: '#FFFFFF',
    backgroundSelected: '#E3ECEA',
    border: 'rgba(17,32,31,0.10)',

    primary: '#0E6E68',
    primaryContainer: '#D8EBE8',
    onPrimaryContainer: '#04302D',

    error: '#9B1C15',
    onError: '#FFFFFF',

    // Score bands. Higher HHS is better, so these run good -> bad.
    bandGood: '#12805C',
    bandMild: '#3E8635',
    bandModerate: '#B4711A',
    bandHigh: '#B23A2E',
  },
  dark: {
    text: '#E4EBEA',
    textSecondary: '#93A3A1',
    background: '#0E1413',
    backgroundElement: '#181F1E',
    backgroundSelected: '#222B2A',
    border: 'rgba(255,255,255,0.10)',

    primary: '#5FB8B1',
    primaryContainer: '#16332F',
    onPrimaryContainer: '#CFE9E5',

    error: '#F2B8B5',
    onError: '#601410',

    bandGood: '#4FBF92',
    bandMild: '#71C05F',
    bandModerate: '#D9A24C',
    bandHigh: '#E07364',
  },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;

/**
 * The resolved palette for whichever scheme is active.
 *
 * Widened to `string` per token on purpose: `Colors` is `as const`, so the two
 * schemes are distinct literal types and a union of them matches neither. Any
 * helper taking a palette wants "a colour", not "this exact hex".
 */
export type Theme = { readonly [K in ThemeColor]: string };

export const Fonts = Platform.select({
  ios: {
    /** iOS `UIFontDescriptorSystemDesignDefault` */
    sans: 'system-ui',
    /** iOS `UIFontDescriptorSystemDesignSerif` */
    serif: 'ui-serif',
    /** iOS `UIFontDescriptorSystemDesignRounded` */
    rounded: 'ui-rounded',
    /** iOS `UIFontDescriptorSystemDesignMonospaced` */
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: 'var(--font-display)',
    serif: 'var(--font-serif)',
    rounded: 'var(--font-rounded)',
    mono: 'var(--font-mono)',
  },
});

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const Radius = { sm: 8, md: 12, lg: 16, xl: 22 } as const;

/** Display faces, loaded in the root layout. Newsreader carries the numbers and
 *  headings; Plus Jakarta Sans does the work. */
export const FontFamily = {
  display: 'Newsreader_600SemiBold',
  displayMedium: 'Newsreader_500Medium',
  body: 'PlusJakartaSans_500Medium',
  bodyBold: 'PlusJakartaSans_700Bold',
  bodySemi: 'PlusJakartaSans_600SemiBold',
} as const;

export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;
export const MaxContentWidth = 800;
