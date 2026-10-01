import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import { NavioraBadge, NavioraCard, NavioraHeader, NavioraText } from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { apiService } from '../../services/api';

export default function AuditLogsScreen() {
  const theme = useTheme();
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadLogs = useCallback(async () => {
    setLoading(true);
    const result = await apiService.get<any>('/admin/audit-logs');
    if (result.data) {
      setLogs(Array.isArray(result.data) ? result.data : result.data.logs || []);
      setError('');
    } else {
      setError(result.error || 'Unable to load audit logs.');
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadLogs(); }, [loadLogs]);

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <NavioraHeader title="Audit Logs" subtitle="System events and user activity" />
        {loading ? <ActivityIndicator color={theme.colors.primary} style={styles.loader} /> : error ? (
          <NavioraText color="danger" style={styles.message}>{error}</NavioraText>
        ) : logs.length === 0 ? (
          <NavioraText color="secondary" style={styles.message}>No audit events available.</NavioraText>
        ) : logs.map((log, index) => (
          <NavioraCard key={String(log.id || index)} style={styles.card}>
            <View style={styles.row}>
              <View style={{ flex: 1 }}>
                <NavioraText type="body" style={{ fontWeight: '700' }}>{log.action || log.event || 'System event'}</NavioraText>
                <NavioraText type="caption" color="secondary">
                  {log.user || log.user_name || 'System'} • {log.created_at ? new Date(log.created_at).toLocaleString() : 'Time unavailable'}
                </NavioraText>
              </View>
              <NavioraBadge label="Logged" tone="success" />
            </View>
          </NavioraCard>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 30 },
  card: { marginTop: 12 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  loader: { marginTop: 32 },
  message: { marginTop: 32, textAlign: 'center' },
});
