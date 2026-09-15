import { StyleSheet, View, type ViewProps } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/**
 * A surface.
 *
 * Every panel on every screen goes through here, so padding, corner radius and
 * the hairline border are decided once. Without it each screen re-invents them
 * slightly differently and the app stops looking like one app.
 */
export function Card({ style, children, ...rest }: ViewProps) {
  const theme = useTheme();

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: theme.backgroundElement, borderColor: theme.border },
        style,
      ]}
      {...rest}>
      {children}
    </View>
  );
}

/** A quiet label above a card, for grouping without a heavy heading. */
export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <ThemedText type="smallBold" themeColor="textSecondary" style={styles.sectionLabel}>
      {children}
    </ThemedText>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: Radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.three,
  },
  sectionLabel: {
    marginTop: Spacing.two,
    marginBottom: Spacing.two,
    marginLeft: Spacing.one,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    fontSize: 11.5,
  },
});
