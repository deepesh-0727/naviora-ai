import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet } from 'react-native';
import { NavioraCard, NavioraHeader, NavioraText } from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { apiService } from '../../services/api';
export default function AdminAnalyticsScreen() {
  const theme = useTheme(); const [data, setData] = useState<any>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const load = useCallback(async () => { setLoading(true); const r = await apiService.get<any>('/admin/analytics'); setData(r.data); setError(r.error || ''); setLoading(false); }, []);
  useEffect(() => { void load(); }, [load]);
  return <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}><ScrollView contentContainerStyle={styles.content}><NavioraHeader title="Analytics" subtitle="Operational performance" />
    {loading ? <ActivityIndicator color={theme.colors.primary} /> : error ? <NavioraText color="danger">{error}</NavioraText> : !data ? <NavioraText color="secondary">No analytics data is available.</NavioraText> : <NavioraCard style={styles.card}><NavioraText type="body" style={{ fontWeight: '700' }}>Current metrics</NavioraText><NavioraText type="caption" color="secondary" style={{ marginTop: 8 }}>{Object.entries(data).map(([key, value]) => `${key}: ${String(value)}`).join(' • ')}</NavioraText></NavioraCard>}
  </ScrollView></SafeAreaView>;
}
const styles = StyleSheet.create({ screen: { flex: 1 }, content: { padding: 20 }, card: { marginTop: 14 } });
