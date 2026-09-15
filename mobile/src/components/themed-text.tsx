import { Platform, StyleSheet, Text, type TextProps } from 'react-native';

import { FontFamily, Fonts, ThemeColor } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export type ThemedTextProps = TextProps & {
  type?: 'default' | 'title' | 'small' | 'smallBold' | 'subtitle' | 'link' | 'linkPrimary' | 'code';
  themeColor?: ThemeColor;
};

export function ThemedText({ style, type = 'default', themeColor, ...rest }: ThemedTextProps) {
  const theme = useTheme();

  return (
    <Text
      style={[
        { color: theme[themeColor ?? 'text'] },
        type === 'default' && styles.default,
        type === 'title' && styles.title,
        type === 'small' && styles.small,
        type === 'smallBold' && styles.smallBold,
        type === 'subtitle' && styles.subtitle,
        type === 'link' && styles.link,
        type === 'linkPrimary' && [styles.linkPrimary, { color: theme.primary }],
        type === 'code' && styles.code,
        style,
      ]}
      {...rest}
    />
  );
}

const styles = StyleSheet.create({
  // Newsreader carries headings and the score; Plus Jakarta Sans does the
  // reading. Two families with clearly different jobs beats one family doing
  // both at different weights.
  title: {
    fontFamily: FontFamily.display,
    fontSize: 34,
    lineHeight: 40,
    letterSpacing: -0.4,
  },
  subtitle: {
    fontFamily: FontFamily.displayMedium,
    fontSize: 24,
    lineHeight: 30,
    letterSpacing: -0.2,
  },
  default: {
    fontFamily: FontFamily.body,
    fontSize: 16,
    lineHeight: 24,
  },
  small: {
    fontFamily: FontFamily.body,
    fontSize: 13.5,
    lineHeight: 19,
  },
  smallBold: {
    fontFamily: FontFamily.bodyBold,
    fontSize: 13.5,
    lineHeight: 19,
  },
  link: {
    fontFamily: FontFamily.bodySemi,
    fontSize: 14,
    lineHeight: 22,
  },
  linkPrimary: {
    fontFamily: FontFamily.bodySemi,
    fontSize: 14,
    lineHeight: 22,
  },
  code: {
    fontFamily: Fonts.mono,
    fontWeight: Platform.select({ android: '700' }) ?? '500',
    fontSize: 12.5,
  },
});
