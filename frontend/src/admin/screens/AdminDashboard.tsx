import React from 'react';
import { Text, View } from 'react-native';
import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { useAdminMetrics } from '../hooks/useAdminMetrics';

export default function AdminDashboard() {
  const { data, loading, error, unavailable, reload } = useAdminMetrics();
  return <ScreenContainer>
    <SectionHeader title="Administration" />
    <Text style={{ color: '#65716B', marginBottom: 10 }}>Live operational metrics and alerts</Text>
    <Button title="Refresh" variant="secondary" onPress={() => void reload()} />
    {loading ? <Loader message="Loading dashboard…" /> : unavailable ? <><BackendNotAvailable endpoint={`GET ${unavailable}`} /><Button title="Retry" variant="secondary" onPress={() => void reload()} /></> : error ? <ErrorState message={error} onRetry={() => void reload()} /> : !data ? <EmptyState message="No dashboard data is available." /> : <>
      <Card style={{ marginTop: 14 }}>{Object.entries(data.kpis).map(([key, value]) => <View key={key} style={{ paddingVertical: 8, flexDirection: 'row', justifyContent: 'space-between' }}><Text>{key.replace(/_/g, ' ')}</Text><Text style={{ fontWeight: '700' }}>{String(value ?? '—')}</Text></View>)}</Card>
      <Card style={{ marginTop: 12 }}><Text style={{ fontWeight: '700', marginBottom: 8 }}>Charts</Text><Text selectable>{JSON.stringify(data.charts, null, 2)}</Text></Card>
      <Card style={{ marginTop: 12 }}><Text style={{ fontWeight: '700', marginBottom: 8 }}>Alerts</Text><Text selectable>{JSON.stringify(data.alerts, null, 2)}</Text></Card>
    </>}
  </ScreenContainer>;
}
