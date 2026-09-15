import { StyleSheet, View, useColorScheme } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Colors } from '@/constants/theme';

/**
 * The score, shown as a filled arc.
 *
 * Drawn with plain Views rather than SVG: the shape is a single rounded bar,
 * and adding react-native-svg for it would be a dependency for one component.
 *
 * Higher is better — the score is 100 minus the burden — which is the opposite
 * of what people expect from anything labelled "cardiovascular burden", so the
 * scale is labelled rather than left to be inferred.
 */

export function bandFor(score: number): { label: string; color: string } {
  // Bands follow the engine's own category wording rather than being invented
  // here, so the colour and the text below it never disagree.
  if (score >= 80) return { label: 'Low burden', color: '#12805C' };
  if (score >= 60) return { label: 'Mild burden', color: '#3E8635' };
  if (score >= 40) return { label: 'Moderate burden', color: '#C8791A' };
  return { label: 'High burden', color: '#C0392B' };
}

export function ScoreDial({ score, category }: { score: number; category: string }) {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'dark' ? 'dark' : 'light'];
  const band = bandFor(score);
  const clamped = Math.max(0, Math.min(100, score));

  return (
    <View style={styles.wrap}>
      <ThemedText style={[styles.score, { color: band.color }]}>
        {score.toFixed(1)}
      </ThemedText>
      <ThemedText type="small" style={styles.outOf}>
        out of 100 — higher is better
      </ThemedText>

      <View style={[styles.track, { backgroundColor: colors.backgroundElement }]}>
        <View
          style={[styles.fill, { width: `${clamped}%`, backgroundColor: band.color }]}
        />
      </View>

      <ThemedText style={styles.category}>{category}</ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: 6 },
  score: { fontSize: 64, fontWeight: '700', lineHeight: 70 },
  outOf: { opacity: 0.7 },
  track: {
    width: '100%',
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
    marginTop: 14,
  },
  fill: { height: '100%', borderRadius: 4 },
  category: { marginTop: 10, fontWeight: '600', textAlign: 'center' },
});
