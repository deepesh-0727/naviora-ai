import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import { NavioraBadge, NavioraButton, NavioraCard, NavioraHeader, NavioraText } from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { apiService } from '../../services/api';

interface QueueItem {
  id: number;
  patient_id: number;
  doctor_id: number;
  position: number;
  status: string;
  priority?: string | number;
}

interface QueueResponse {
  items: QueueItem[];
}

export default function NurseQueueScreen() {
  const theme = useTheme();
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.get<QueueResponse>('/queue/status');
      if (!result.data) {
        setError(result.error || 'Queue data is unavailable.');
        return;
      }
      setQueue(Array.isArray(result.data.items) ? result.data.items : []);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load the queue.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const completeAppointment = async (appointmentId: number) => {
    setSavingId(appointmentId);
    setError(null);
    try {
      const result = await apiService.put<QueueItem>(`/queue/complete/${appointmentId}`, {});
      if (result.error || !result.data) {
        setError(result.error || 'Unable to complete this appointment.');
        return;
      }
      await load();
    } catch (mutationError) {
      setError(mutationError instanceof Error ? mutationError.message : 'Unable to complete this appointment.');
    } finally {
      setSavingId(null);
    }
  };

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <NavioraHeader title="Queue Management" subtitle="Live check-in and patient flow" showBack={false} />
        <NavioraButton title="Refresh queue" variant="secondary" onPress={() => void load()} style={styles.refresh} />
        {loading ? <ActivityIndicator color={theme.colors.primary} style={styles.loader} /> : null}
        {error ? <NavioraText color="danger" style={styles.message}>{error}</NavioraText> : null}
        {!loading && !error && queue.length === 0 ? (
          <NavioraText color="secondary" style={styles.empty}>No active queue entries are available.</NavioraText>
        ) : null}
        {queue.map(item => (
          <NavioraCard key={String(item.id)} style={styles.card}>
            <View style={styles.row}>
              <View style={styles.entry}>
                <NavioraText type="body" style={{ fontWeight: '700' }}>Appointment #{item.id}</NavioraText>
                <NavioraText type="caption" color="secondary">Patient #{item.patient_id} · Doctor #{item.doctor_id}</NavioraText>
                <NavioraText type="caption" color="secondary">Queue position {item.position}</NavioraText>
              </View>
              <NavioraBadge label={item.status} tone="info" />
            </View>
            <NavioraButton
              title="Mark complete"
              variant="secondary"
              onPress={() => void completeAppointment(item.id)}
              loading={savingId === item.id}
              disabled={savingId !== null}
              style={styles.action}
            />
          </NavioraCard>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { padding: 20, paddingBottom: 32 },
  refresh: { marginTop: 12 },
  loader: { marginTop: 28 },
  message: { marginTop: 14 },
  empty: { marginTop: 24 },
  card: { marginTop: 14 },
  row: { flexDirection: 'row', alignItems: 'center' },
  entry: { flex: 1 },
  action: { marginTop: 14 },
});
