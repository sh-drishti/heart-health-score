import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
  useColorScheme,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { fetchDashboard, type Dashboard, type DomainRow } from '@/api/me';
import { useSession } from '@/auth/ctx';
import { ScoreDial } from '@/components/score-dial';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, Colors, Spacing } from '@/constants/theme';

/**
 * The patient's own score.
 *
 * Leads with the number and what it means, then where the burden comes from —
 * which is the only part anyone can act on. Raw severities (0.429) and the
 * 127-field parameter dump are deliberately not shown: they are for the
 * clinical dashboard, not for the person.
 */

const STATUS_COLOR: Record<string, string> = {
  Low: '#12805C',
  Mild: '#3E8635',
  Moderate: '#C8791A',
  High: '#C0392B',
};

function DomainBar({ row, maxContribution }: { row: DomainRow; maxContribution: number }) {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'dark' ? 'dark' : 'light'];
  const color = STATUS_COLOR[row.Status] ?? colors.textSecondary;
  const contribution = row['Total domain contribution'];

  // Bars are relative to the largest contributor rather than to the total, so
  // the biggest one fills the row and the differences stay readable.
  const width = maxContribution > 0 ? (contribution / maxContribution) * 100 : 0;

  return (
    <View style={styles.domainRow}>
      <View style={styles.domainHeader}>
        <ThemedText style={styles.domainName}>{row.Domain}</ThemedText>
        <ThemedText type="small" style={{ color }}>
          {row.Status}
        </ThemedText>
      </View>
      <View style={[styles.domainTrack, { backgroundColor: colors.backgroundElement }]}>
        <View style={[styles.domainFill, { width: `${width}%`, backgroundColor: color }]} />
      </View>
    </View>
  );
}

export default function Today() {
  const { user, signOut } = useSession();
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'dark' ? 'dark' : 'light'];

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
      setError(
        e instanceof ApiError ? e.message : 'Could not load your score right now.',
      );
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
        <ActivityIndicator />
      </ThemedView>
    );
  }

  const assessment = data?.assessment;
  const domains = assessment
    ? [...assessment.domain_rows].sort(
        (a, b) => b['Total domain contribution'] - a['Total domain contribution'],
      )
    : [];
  const maxContribution = domains.length ? domains[0]['Total domain contribution'] : 0;

  return (
    <ThemedView style={styles.fill}>
      <SafeAreaView style={styles.fill} edges={['top']}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} />
          }>
          <View style={styles.greeting}>
            <ThemedText type="small" style={styles.hello}>
              {user?.name ? `Hello, ${user.name.split(' ')[0]}` : 'Hello'}
            </ThemedText>
            {data?.visit?.visit_date ? (
              <ThemedText type="small" style={styles.asOf}>
                As of {data.visit.visit_date}
              </ThemedText>
            ) : null}
          </View>

          {error ? (
            <View style={[styles.card, { backgroundColor: colors.backgroundElement }]}>
              <ThemedText style={styles.errorText}>{error}</ThemedText>
              <Pressable onPress={() => load(true)} style={styles.retry}>
                <ThemedText type="link">Try again</ThemedText>
              </Pressable>
            </View>
          ) : null}

          {assessment ? (
            <>
              <View style={[styles.card, { backgroundColor: colors.backgroundElement }]}>
                <ScoreDial score={assessment.hhs} category={assessment.category} />
              </View>

              <View style={[styles.card, { backgroundColor: colors.backgroundElement }]}>
                <ThemedText type="small" style={styles.cardLabel}>
                  How complete your information is
                </ThemedText>
                <ThemedText style={styles.confidence}>
                  {assessment.data_confidence.toFixed(0)}%{' '}
                  <ThemedText type="small">({assessment.confidence_label})</ThemedText>
                </ThemedText>
                {/* Said plainly because the two are easy to confuse, and
                    confusing them is the difference between "my heart is fine"
                    and "we know enough to say". */}
                <ThemedText type="small" style={styles.hint}>
                  This is how much of your information we have — not how certain
                  your result is. Filling in more moves your score toward
                  {' '}{assessment.score_interval.optimistic.toFixed(1)} or
                  {' '}{assessment.score_interval.floor.toFixed(1)} as things are
                  confirmed.
                </ThemedText>
              </View>

              <ThemedText type="small" style={styles.sectionLabel}>
                What is affecting your score
              </ThemedText>
              <View style={[styles.card, { backgroundColor: colors.backgroundElement }]}>
                {domains.map((row) => (
                  <DomainBar key={row.Domain} row={row} maxContribution={maxContribution} />
                ))}
              </View>

              {assessment.recommended_inputs?.length ? (
                <>
                  <ThemedText type="small" style={styles.sectionLabel}>
                    Worth adding
                  </ThemedText>
                  <View style={[styles.card, { backgroundColor: colors.backgroundElement }]}>
                    {assessment.recommended_inputs.map((rec) => (
                      <View key={rec.Field} style={styles.recRow}>
                        <ThemedText>{rec.Field}</ThemedText>
                        <ThemedText type="small" style={styles.recDomain}>
                          {rec.Domain}
                        </ThemedText>
                      </View>
                    ))}
                  </View>
                </>
              ) : null}

              <ThemedText type="small" style={styles.disclaimer}>
                Research prototype only — not validated for clinical
                decision-making. Talk to a doctor about anything that concerns
                you.
              </ThemedText>
            </>
          ) : null}

          <Pressable onPress={signOut} style={styles.signOut}>
            <ThemedText type="link">Sign out</ThemedText>
          </Pressable>
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll: { padding: Spacing.three, paddingBottom: BottomTabInset + Spacing.five, gap: 12 },
  greeting: { marginBottom: 4 },
  hello: { fontSize: 15 },
  asOf: { opacity: 0.6 },
  card: { borderRadius: 14, padding: Spacing.three },
  cardLabel: { opacity: 0.7, marginBottom: 4 },
  confidence: { fontSize: 28, fontWeight: '700' },
  hint: { opacity: 0.7, marginTop: 8, lineHeight: 18 },
  sectionLabel: { opacity: 0.7, marginTop: 8, marginLeft: 4 },
  domainRow: { marginBottom: 14 },
  domainHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  domainName: { fontWeight: '500' },
  domainTrack: { height: 6, borderRadius: 3, overflow: 'hidden' },
  domainFill: { height: '100%', borderRadius: 3 },
  recRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  recDomain: { opacity: 0.6 },
  errorText: { marginBottom: 8 },
  retry: { paddingVertical: 4 },
  disclaimer: { opacity: 0.55, marginTop: 12, lineHeight: 17, paddingHorizontal: 4 },
  signOut: { alignItems: 'center', paddingVertical: Spacing.three, marginTop: 8 },
});
