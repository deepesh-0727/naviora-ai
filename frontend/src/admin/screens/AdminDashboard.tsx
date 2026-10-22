import { colors } from '../../shared/theme/colors';
import React from 'react';
import { Text, View } from 'react-native';
import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { useAdminMetrics } from '../hooks/useAdminMetrics';

type AppointmentChartRow = { date?: string; status?: string; count?: number };

export default function AdminDashboard() {
  const { data, loading, error, unavailable, reload } = useAdminMetrics();
  const chartRows = Array.isArray(data?.charts.appointments_by_day_and_status)
    ? data.charts.appointments_by_day_and_status as AppointmentChartRow[]
    : [];
  const activeEmergencies = Array.isArray(data?.alerts.active_emergencies) ? data.alerts.active_emergencies.length : 0;
  const recentAccessDenials = Array.isArray(data?.alerts.recent_access_denials) ? data.alerts.recent_access_denials.length : 0;

  return <ScreenContainer>
    <SectionHeader title="Administration" />
    <Text style={{ color: colors.textMuted, marginBottom: 10 }}>Live operational metrics and alerts</Text>
    <Button title="Refresh" variant="secondary" onPress={() => void reload()} />
    {loading ? <Loader message="Loading dashboard…" /> : unavailable ? <><BackendNotAvailable endpoint={`GET ${unavailable}`} /><Button title="Retry" variant="secondary" onPress={() => void reload()} /></> : error ? <ErrorState message={error} onRetry={() => void reload()} /> : !data ? <EmptyState message="No dashboard data is available." /> : <>
      <Card style={{ marginTop: 14 }}>{Object.entries(data.kpis).map(([key, value]) => <View key={key} style={{ paddingVertical: 8, flexDirection: 'row', justifyContent: 'space-between' }}><Text>{key.replace(/_/g, ' ')}</Text><Text style={{ fontWeight: '700' }}>{String(value ?? '—')}</Text></View>)}</Card>
      <Card style={{ marginTop: 12 }}>
        <Text style={{ fontWeight: '700', marginBottom: 8 }}>Appointment flow</Text>
        {chartRows.length === 0 ? <Text style={{ color: colors.textMuted }}>No appointment data yet.</Text> : chartRows.map((row, index) => (
          <View key={`${row.date ?? 'date'}-${row.status ?? 'status'}-${index}`} style={{ paddingVertical: 6, flexDirection: 'row', justifyContent: 'space-between' }}>
            <Text style={{ color: colors.textMuted }}>{row.date ?? '—'} · {row.status ?? 'Unknown status'}</Text>
            <Text style={{ fontWeight: '700' }}>{row.count ?? 0}</Text>
          </View>
        ))}
      </Card>
      <Card style={{ marginTop: 12 }}>
        <Text style={{ fontWeight: '700', marginBottom: 8 }}>Alerts</Text>
        <Text style={{ color: colors.textMuted }}>Active emergencies: {activeEmergencies}</Text>
        <Text style={{ color: colors.textMuted, marginTop: 4 }}>Recent access denials: {recentAccessDenials}</Text>
      </Card>
    </>}
  </ScreenContainer>;
}
