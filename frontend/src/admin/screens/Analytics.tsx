import React, { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { StyleSheet, Text, View } from 'react-native';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { Button, Card, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type AdminKpis = { patients_total?: number; appointments_total?: number };

export default function Analytics() {
  const [metrics, setMetrics] = useState<AdminKpis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<AdminKpis>(buildApiUrl('admin', '/dashboard/kpis'));
      setMetrics(response.data);
    } catch (cause) {
      setError(isAxiosError(cause) && cause.response?.status === 500
        ? 'The server could not load analytics. Please retry shortly.'
        : 'Could not load analytics totals.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return <ScreenContainer>
    <SectionHeader title="Analytics" />
    <Text style={styles.description}>Hospital activity totals from the live database</Text>
    <Button title="Refresh" variant="secondary" onPress={() => void load()} />
    {loading ? <Loader message="Loading analytics…" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : <View style={styles.cards}>
      <Card style={styles.metricCard}><Text style={styles.metricLabel}>Total Patients</Text><Text style={styles.metricValue}>{metrics?.patients_total ?? 0}</Text></Card>
      <Card style={styles.metricCard}><Text style={styles.metricLabel}>Total Appointments</Text><Text style={styles.metricValue}>{metrics?.appointments_total ?? 0}</Text></Card>
    </View>}
  </ScreenContainer>;
}

const styles = StyleSheet.create({
  description: { color: colors.textMuted, marginBottom: 12 },
  cards: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 14 },
  metricCard: { flexGrow: 1, flexBasis: '45%', minHeight: 110, justifyContent: 'center' },
  metricLabel: { color: colors.textMuted, fontSize: 14, fontWeight: '600' },
  metricValue: { color: colors.primary, fontSize: 30, fontWeight: '700', marginTop: 8 },
});
