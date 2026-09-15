import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { fetchDashboard, type Dashboard, type DomainRow } from '@/api/me';
import { useSession } from '@/auth/ctx';
import { Card, SectionLabel } from '@/components/card';
import { bandFor, ScoreRing } from '@/components/score-ring';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, Radius, Spacing, type Theme } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/**
 * The patient's own score.
 *
 * Leads with the number and what it means, then where the burden comes from —
 * the only part anyone can act on. Raw severities and the 127-field parameter
 * dump stay out: they are the clinical dashboard's material, not the person's.
 */

function statusColor(status: string, theme: Theme): string {
  switch (status) {
    case 'Low':
      return theme.bandGood;
    case 'Mild':
      return theme.bandMild;
    case 'Moderate':
      return theme.bandModerate;
    case 'High':
      return theme.bandHigh;
    default:
      return theme.textSecondary;
  }
}

function DomainBar({ row, max }: { row: DomainRow; max: number }) {
  const theme = useTheme();
  const color = statusColor(row.Status, theme);
  // Relative to the largest contributor rather than to the total, so the
  // biggest fills the row and the differences between the rest stay legible.
  const width = max > 0 ? (row['Total domain contribution'] / max) * 100 : 0;

  return (
    <View style={styles.domainRow}>
      <View style={styles.domainHeader}>
        <ThemedText type="small" style={styles.domainName}>
          {row.Domain}
        </ThemedText>
        <ThemedText type="smallBold" style={{ color }}>
          {row.Status}
        </ThemedText>
      </View>
      <View style={[styles.domainTrack, { backgroundColor: theme.backgroundSelected }]}>
        <View
          style={[styles.domainFill, { width: `${width}%`, backgroundColor: color }]}
        />
      </View>
    </View>
  );
}

export default function Today() {
  const { user, signOut } = useSession();
  const theme = useTheme();

  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    setError(null);
    try {
      setData(await fetchDashboard());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not load your score.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <ThemedView style={styles.center}>
        <ActivityIndicator color={theme.primary} />
      </ThemedView>
    );
  }

  const assessment = data?.assessment;
  const domains = assessment
    ? [...assessment.domain_rows].sort(
        (a, b) => b['Total domain contribution'] - a['Total domain contribution'],
      )
    : [];
  const max = domains.length ? domains[0]['Total domain contribution'] : 0;
  const band = assessment ? bandFor(assessment.hhs, theme) : null;

  return (
    <ThemedView style={styles.fill}>
      <SafeAreaView style={styles.fill} edges={['top']}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => load(true)}
              tintColor={theme.textSecondary}
            />
          }>
          <View style={styles.header}>
            <ThemedText type="title">
              {user?.name ? user.name.split(' ')[0] : 'Your heart'}
            </ThemedText>
            {data?.visit?.visit_date ? (
              <ThemedText type="small" themeColor="textSecondary">
                Last updated {data.visit.visit_date}
              </ThemedText>
            ) : null}
          </View>

          {error ? (
            <Card style={{ borderColor: theme.error }}>
              <ThemedText type="small" style={{ color: theme.error }}>
                {error}
              </ThemedText>
              <Pressable onPress={() => load(true)} hitSlop={8}>
                <ThemedText type="linkPrimary">Try again</ThemedText>
              </Pressable>
            </Card>
          ) : null}

          {assessment && band ? (
            <>
              <Card style={styles.scoreCard}>
                <ScoreRing
                  score={assessment.hhs}
                  optimistic={assessment.score_interval.optimistic}
                />
                <View style={[styles.pill, { backgroundColor: `${band.color}1A` }]}>
                  <View style={[styles.dot, { backgroundColor: band.color }]} />
                  <ThemedText type="smallBold" style={{ color: band.color }}>
                    {assessment.category}
                  </ThemedText>
                </View>
                <ThemedText
                  type="small"
                  themeColor="textSecondary"
                  style={styles.higherBetter}>
                  Higher is better — the score is what remains after your risk
                  factors are counted.
                </ThemedText>
              </Card>

              <SectionLabel>What is affecting your score</SectionLabel>
              <Card>
                {domains.map((row, i) => (
                  <View
                    key={row.Domain}
                    style={i === domains.length - 1 ? styles.lastRow : undefined}>
                    <DomainBar row={row} max={max} />
                  </View>
                ))}
              </Card>

              <SectionLabel>How complete your information is</SectionLabel>
              <Card>
                <View style={styles.confidenceRow}>
                  <ThemedText type="subtitle">
                    {assessment.data_confidence.toFixed(0)}%
                  </ThemedText>
                  <ThemedText type="smallBold" themeColor="primary">
                    {assessment.confidence_label}
                  </ThemedText>
                </View>
                <ThemedText
                  type="small"
                  themeColor="textSecondary"
                  style={styles.hint}>
                  This is how much of your information we have — not how certain
                  your result is. As more is confirmed your score settles
                  somewhere between {assessment.score_interval.floor.toFixed(1)} and{' '}
                  {assessment.score_interval.optimistic.toFixed(1)}.
                </ThemedText>
              </Card>

              {assessment.recommended_inputs?.length ? (
                <>
                  <SectionLabel>Worth adding</SectionLabel>
                  <Card>
                    {assessment.recommended_inputs.map((rec, i) => (
                      <View
                        key={rec.Field}
                        style={[
                          styles.recRow,
                          i > 0 && { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: theme.border },
                        ]}>
                        <ThemedText type="small">{rec.Field}</ThemedText>
                        <ThemedText type="small" themeColor="textSecondary">
                          {rec.Domain}
                        </ThemedText>
                      </View>
                    ))}
                  </Card>
                </>
              ) : null}

              <ThemedText
                type="small"
                themeColor="textSecondary"
                style={styles.disclaimer}>
                Research prototype — not validated for clinical decision-making.
                Talk to a doctor about anything that concerns you.
              </ThemedText>
            </>
          ) : null}

          <Pressable onPress={signOut} style={styles.signOut} hitSlop={8}>
            <ThemedText type="link" themeColor="textSecondary">
              Sign out
            </ThemedText>
          </Pressable>
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll: {
    paddingHorizontal: Spacing.three,
    paddingBottom: BottomTabInset + Spacing.five,
  },
  header: { paddingTop: Spacing.two, paddingBottom: Spacing.four, gap: 2 },
  scoreCard: { alignItems: 'center', paddingVertical: Spacing.four },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 13,
    paddingVertical: 7,
    borderRadius: Radius.xl,
    marginTop: Spacing.three,
  },
  dot: { width: 7, height: 7, borderRadius: 4 },
  higherBetter: {
    textAlign: 'center',
    marginTop: Spacing.three,
    paddingHorizontal: Spacing.two,
  },
  domainRow: { marginBottom: Spacing.three },
  lastRow: { marginBottom: -Spacing.three },
  domainHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 7,
  },
  domainName: { fontSize: 15 },
  domainTrack: { height: 7, borderRadius: 4, overflow: 'hidden' },
  domainFill: { height: '100%', borderRadius: 4 },
  confidenceRow: { flexDirection: 'row', alignItems: 'baseline', gap: 10 },
  hint: { marginTop: Spacing.two, lineHeight: 19 },
  recRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 11 },
  disclaimer: {
    marginTop: Spacing.four,
    paddingHorizontal: Spacing.one,
    lineHeight: 18,
    opacity: 0.75,
  },
  signOut: { alignItems: 'center', paddingVertical: Spacing.four },
});
