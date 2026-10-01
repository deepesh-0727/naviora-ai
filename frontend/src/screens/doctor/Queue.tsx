import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../context/ThemeContext';
import { NavioraText, GlassCard, NavioraHeader, NavioraTabSelector } from '../../components/common/AtomicComponents';
import { apiService } from '../../services/api';

interface QueueEntry {
  id: number;
  patient_id: number;
  doctor_id: number;
  position: number;
  status: string;
  priority?: string | number;
}

interface QueueResponse {
  items: QueueEntry[];
}

interface DoctorIdentity {
  id: number;
}

interface AppointmentResult {
  id: number;
  status: string;
}

export default function DoctorQueueScreen({ navigation }: any) {
  const theme = useTheme();
  const [tab, setTab] = useState(0);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [callingNext, setCallingNext] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [doctorId, setDoctorId] = useState<number | null>(null);
  const tabs = ['All', 'Urgent', 'Waiting', 'Done'];

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [profileResult, queueResult] = await Promise.all([
        apiService.get<DoctorIdentity>('/doctors/profile'),
        apiService.get<QueueResponse>('/queue/status'),
      ]);
      if (!profileResult.data || !queueResult.data) {
        setError(profileResult.error || queueResult.error || 'Queue data is unavailable.');
        return;
      }
      setDoctorId(profileResult.data.id);
      setQueue(Array.isArray(queueResult.data.items) ? queueResult.data.items : []);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load the queue.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadQueue(); }, [loadQueue]);

  const callNextPatient = async () => {
    if (doctorId === null || callingNext) return;
    setCallingNext(true);
    setError(null);
    try {
      const result = await apiService.post<AppointmentResult>(`/queue/next/${doctorId}`, {});
      if (result.error || !result.data) {
        setError(result.error || 'No checked-in patient is currently available to call.');
        return;
      }
      await loadQueue();
    } catch (mutationError) {
      setError(mutationError instanceof Error ? mutationError.message : 'Unable to call the next patient.');
    } finally {
      setCallingNext(false);
    }
  };

  const filtered = tab === 0 ? queue
    : tab === 1 ? queue.filter(item => {
      const priority = String(item.priority || '').toLowerCase();
      return priority.includes('urgent') || priority.includes('critical') || priority.includes('high')
        || (priority !== '' && Number(priority) <= 2);
    })
    : tab === 2 ? queue.filter(item => item.status === 'check_in' || item.status === 'scheduled')
    : [];
  const nextEntry = queue.find(item => item.status === 'check_in');
  const waitingCount = queue.filter(item => item.status === 'check_in').length;

  const emptyMessage = tab === 1
    ? 'No urgent queue entries are reported.'
    : tab === 3
      ? 'Completed appointments are not part of the active queue.'
      : 'No patients are currently in the active queue.';

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <NavioraHeader
        title="Patient Queue"
        subtitle={loading ? 'Loading current queue…' : error ? 'Queue unavailable' : `${waitingCount} checked-in patients`}
        showBack={false}
      />
      <View style={{ paddingHorizontal: 16, paddingBottom: 8 }}>
        <NavioraTabSelector tabs={tabs} activeTab={tab} onChange={setTab} />
      </View>
      {error ? (
        <View style={styles.errorBanner}>
          <NavioraText type="caption" color="error">{error}</NavioraText>
          <TouchableOpacity onPress={() => void loadQueue()}>
            <NavioraText type="label" color="primary" style={{ marginTop: 8 }}>Refresh</NavioraText>
          </TouchableOpacity>
        </View>
      ) : null}

      {!loading && !error && nextEntry ? (
        <GlassCard style={[styles.currentCard, { backgroundColor: theme.colors.primary }]}>
          <View style={styles.currentRow}>
            <View>
              <NavioraText type="xs" color="inverse" style={{ opacity: 0.7 }}>NEXT IN QUEUE</NavioraText>
              <NavioraText type="h3" color="inverse">Appointment #{nextEntry.id}</NavioraText>
              <NavioraText type="caption" color="inverse" style={{ opacity: 0.75 }}>
                Patient #{nextEntry.patient_id} · Position {nextEntry.position}
              </NavioraText>
            </View>
            <TouchableOpacity
              style={styles.nextBtn}
              onPress={() => navigation.navigate('PatientDetails', { patient: nextEntry })}
            >
              <NavioraText type="label" color="inverse">View →</NavioraText>
            </TouchableOpacity>
          </View>
        </GlassCard>
      ) : null}

      <FlatList
        data={filtered}
        keyExtractor={item => String(item.id)}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 100 }}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            {loading ? (
              <ActivityIndicator size="large" color={theme.colors.primary} />
            ) : error ? (
              <>
                <NavioraText type="body" color="error" align="center">{error}</NavioraText>
                <TouchableOpacity onPress={() => void loadQueue()}>
                  <NavioraText type="label" color="primary" style={{ marginTop: 12 }}>Try again</NavioraText>
                </TouchableOpacity>
              </>
            ) : (
              <NavioraText type="body" color="low" align="center">{emptyMessage}</NavioraText>
            )}
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.queueItem, { borderLeftColor: theme.colors.primaryLight, backgroundColor: theme.colors.surface }]}
            onPress={() => navigation.navigate('PatientDetails', { patient: item })}
          >
            <View style={[styles.tokenBadge, { backgroundColor: theme.colors.primaryLight }]}>
              <NavioraText type="label" color="primary">#{item.position}</NavioraText>
            </View>
            <View style={{ flex: 1, marginLeft: 14 }}>
              <NavioraText type="body">Appointment #{item.id}</NavioraText>
              <NavioraText type="caption" color="low">Patient #{item.patient_id} · {item.status}</NavioraText>
            </View>
          </TouchableOpacity>
        )}
        ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
      />

      <TouchableOpacity
        style={[styles.fab, { backgroundColor: theme.colors.primary, opacity: callingNext ? 0.65 : 1 }]}
        onPress={() => void callNextPatient()}
        disabled={callingNext || doctorId === null || waitingCount === 0}
      >
        {callingNext ? <ActivityIndicator color="#fff" /> : <Ionicons name="arrow-forward-circle" size={24} color="#fff" />}
        <NavioraText type="label" color="inverse" style={{ marginLeft: 8 }}>Call Next Patient</NavioraText>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  currentCard: { margin: 16, padding: 16, borderRadius: 16 },
  currentRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  nextBtn: { paddingHorizontal: 14, paddingVertical: 8, backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: 12 },
  emptyState: { paddingHorizontal: 24, paddingTop: 36, alignItems: 'center' },
  errorBanner: { marginHorizontal: 16, marginBottom: 8, padding: 12, borderRadius: 12, backgroundColor: '#FEE2E2' },
  queueItem: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 14, borderLeftWidth: 4, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  tokenBadge: { width: 52, height: 52, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  fab: { position: 'absolute', bottom: 24, alignSelf: 'center', flexDirection: 'row', alignItems: 'center', paddingHorizontal: 24, paddingVertical: 14, borderRadius: 30, elevation: 4, shadowColor: '#3A5A40', shadowOpacity: 0.3, shadowRadius: 12 },
});
