import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';
import Svg, { Circle, G } from 'react-native-svg';

import { ThemedText } from '@/components/themed-text';
import { FontFamily, type Theme } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

const SIZE = 210;
const STROKE = 14;
const R = (SIZE - STROKE) / 2;
const CIRC = 2 * Math.PI * R;

/**
 * Which band a score falls in.
 *
 * Bands run good -> bad as the number falls, because the score is 100 minus
 * the burden. Colours come from the palette rather than being written here, so
 * a band never disagrees with itself across two screens.
 */
export function bandFor(score: number, theme: Theme): { label: string; color: string } {
  if (score >= 80) return { label: 'Low burden', color: theme.bandGood };
  if (score >= 60) return { label: 'Mild burden', color: theme.bandMild };
  if (score >= 40) return { label: 'Moderate burden', color: theme.bandModerate };
  return { label: 'High burden', color: theme.bandHigh };
}

interface Props {
  score: number;
  /** Where the score could sit once missing information is filled in. Drawn as
   *  a faint second arc, so the number reads as an estimate rather than a
   *  verdict. */
  optimistic?: number;
}

export function ScoreRing({ score, optimistic }: Props) {
  const theme = useTheme();
  const band = bandFor(score, theme);

  const clamped = Math.max(0, Math.min(100, score)) / 100;
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(progress, {
      toValue: clamped,
      duration: 900,
      // strokeDashoffset cannot run on the native driver.
      useNativeDriver: false,
    }).start();
  }, [clamped, progress]);

  const dashOffset = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [CIRC, 0],
  });

  const headroom =
    optimistic !== undefined && optimistic > score
      ? Math.max(0, Math.min(100, optimistic)) / 100
      : null;

  return (
    <View style={styles.wrap}>
      <Svg width={SIZE} height={SIZE} style={styles.svg}>
        <Circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={R}
          stroke={theme.backgroundSelected}
          strokeWidth={STROKE}
          fill="none"
        />
        <G transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}>
          {headroom !== null ? (
            <Circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={R}
              stroke={band.color}
              strokeOpacity={0.22}
              strokeWidth={STROKE}
              fill="none"
              strokeDasharray={`${CIRC * headroom} ${CIRC}`}
              strokeLinecap="round"
            />
          ) : null}
          <AnimatedCircle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={R}
            stroke={band.color}
            strokeWidth={STROKE}
            fill="none"
            strokeDasharray={`${CIRC} ${CIRC}`}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
          />
        </G>
      </Svg>

      <View style={styles.center}>
        <ThemedText style={[styles.score, { color: theme.text }]}>
          {score.toFixed(1)}
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary" style={styles.outOf}>
          out of 100
        </ThemedText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: SIZE, height: SIZE, alignItems: 'center', justifyContent: 'center' },
  svg: { position: 'absolute' },
  center: { alignItems: 'center' },
  score: {
    fontFamily: FontFamily.display,
    fontSize: 58,
    lineHeight: 64,
    letterSpacing: -1,
  },
  outOf: { marginTop: 2 },
});
