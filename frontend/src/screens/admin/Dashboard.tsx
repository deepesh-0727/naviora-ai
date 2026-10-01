import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import { NavioraAvatar, NavioraCard, NavioraHeader, NavioraStatCard, NavioraText } from '../../components/common/AtomicComponents';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { apiService } from '../../services/api';

export default function AdminDashboardScreen() {
  const theme = useTheme();
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    setLoading(true);
    const result = await apiService.get<any>('/admin/analytics');
    setMetrics(result.data);
    setError(result.error || '');
    setLoading(false);
  }, []);
  useEffect(() => { void load(); }, [load]);
  const value = (key: string) => metrics?.[key] ?? metrics?.kpis?.[key] ?? '—';
  return <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
    <ScrollView contentContainerStyle={styles.content}>
      <NavioraHeader title={`Welcome, ${user?.name || 'Administrator'}`} subtitle="Operations overview" right={<NavioraAvatar initials={(user?.name || 'AD').slice(0, 2).toUpperCase()} size={42} online />} />
      {loading ? <ActivityIndicator color={theme.colors.primary} /> : error ? <NavioraText color="danger">{error}</NavioraText> : !metrics ? <NavioraText color="secondary">No operational metrics are available.</NavioraText> :
        <View style={styles.statsRow}>
          <NavioraStatCard icon="calendar" value={String(value('appointments_today'))} label="Appointments" meta="Today" accent="primary" />
          <NavioraStatCard icon="time" value={String(value('average_wait_minutes'))} label="Wait Time" meta="Avg" accent="amber" />
          <NavioraStatCard icon="alert-circle" value={String(value('active_emergencies'))} label="Emergencies" meta="Active" accent="red" />
          <NavioraStatCard icon="cash" value={String(value('revenue'))} label="Revenue" meta="Current period" accent="blue" />
        </View>}
      <NavioraCard style={styles.card}><NavioraText type="body">Metrics are loaded from the administration service.</NavioraText></NavioraCard>
    </ScrollView>
  </SafeAreaView>;
}
const styles = StyleSheet.create({ screen: { flex: 1 }, content: { padding: 20 }, statsRow: { flexDirection: 'row', marginTop: 14 }, card: { marginTop: 18 } });
