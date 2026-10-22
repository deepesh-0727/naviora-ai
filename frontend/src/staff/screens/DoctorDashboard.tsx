import { colors } from '../../shared/theme/colors';
import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Header, Loader, ScreenContainer } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';

type Entry = Record<string, unknown>;
interface DashboardData { schedule: Entry[]; queue: Entry[]; stats: Entry | null; }
const emptyData: DashboardData = { schedule: [], queue: [], stats: null };

function records(value: unknown): Entry[] {
  if (Array.isArray(value)) return value.filter((entry): entry is Entry => typeof entry === 'object' && entry !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) {
    return value.items.filter((entry): entry is Entry => typeof entry === 'object' && entry !== null);
  }
  return [];
}

function field(entry: Entry, keys: string[]): string {
  for (const key of keys) {
    const value = entry[key];
    if (typeof value === 'string' || typeof value === 'number') return String(value);
  }
  return '—';
}

export default function DoctorDashboard() {
  const [data, setData] = useState<DashboardData>(emptyData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [missingEndpoint, setMissingEndpoint] = useState<string | null>(null);
  const [emergencyAlert, setEmergencyAlert] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    setMissingEndpoint(null);
    try {
      const [schedule, queue, stats] = await Promise.all([
        apiClient.get<unknown>(buildApiUrl('doctor', '/doctor/schedule?date=today')),
        apiClient.get<unknown>(buildApiUrl('doctor', '/doctor/queue')),
        apiClient.get<unknown>(buildApiUrl('doctor', '/doctor/stats/today')),
      ]);
      setData({
        schedule: records(schedule.data),
        queue: records(queue.data),
        stats: typeof stats.data === 'object' && stats.data !== null ? stats.data as Entry : null,
      });
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason
        ? (reason as { response?: { status?: number }; config?: { url?: string } }).response?.status
        : undefined;
      const url = typeof reason === 'object' && reason !== null && 'config' in reason
        ? (reason as { config?: { url?: string } }).config?.url
        : undefined;
      if (status === 404 || status === 501) setMissingEndpoint(url ?? 'GET /staff/doctor/schedule');
      else if (status === 500) setError('The server could not load doctor data. Check the backend database logs and try again.');
      else setError('Could not load today’s doctor dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    void websocketClient.connect();
    const unsubscribeQueue = websocketClient.subscribe('queue_update', () => { void refresh(); });
    const unsubscribeEmergency = websocketClient.subscribe('emergency_new', () => setEmergencyAlert(true));
    return () => { unsubscribeQueue(); unsubscribeEmergency(); };
  }, [refresh]);

  if (loading) return <ScreenContainer><Header title="Doctor Dashboard" /><Loader message="Loading your schedule…" /></ScreenContainer>;
  if (missingEndpoint) return <ScreenContainer><Header title="Doctor Dashboard" /><BackendNotAvailable endpoint={missingEndpoint} /><Button title="Retry" variant="secondary" onPress={() => void refresh()} /></ScreenContainer>;
  if (error) return <ScreenContainer><Header title="Doctor Dashboard" /><ErrorState message={error} onRetry={() => void refresh()} /></ScreenContainer>;
  if (data.stats === null && data.schedule.length === 0 && data.queue.length === 0) {
    return <ScreenContainer><Header title="Doctor Dashboard" /><EmptyState message="No schedule or queue entries for today." /><Button title="Refresh" variant="secondary" onPress={() => void refresh()} /></ScreenContainer>;
  }

  return (
    <ScreenContainer>
      <ScrollView contentContainerStyle={{ paddingBottom: 100 }}>
        <Header title="Doctor Dashboard" />
        {emergencyAlert ? <Card style={{ marginBottom: 12, backgroundColor: colors.dangerLight }}><Text style={{ color: colors.danger, fontWeight: '700' }}>New emergency response requested.</Text></Card> : null}
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
          {[
            { key: 'total_patients', icon: 'people-outline' as const },
            { key: 'completed', icon: 'checkmark-circle-outline' as const },
            { key: 'waiting', icon: 'time-outline' as const },
            { key: 'pending_prescriptions', icon: 'medkit-outline' as const },
          ].map(({ key, icon }) => (
            <Card key={key} style={{ flexBasis: '47%', flexGrow: 1, minWidth: 140 }}>
              <Ionicons name={icon} size={20} color={colors.primary} />
              <Text style={{ fontSize: 24, fontWeight: '700', color: colors.text, marginTop: 8 }}>{field(data.stats ?? {}, [key])}</Text>
              <Text style={{ color: colors.textMuted }}>{key.split('_').join(' ')}</Text>
            </Card>
          ))}
        </View>
        <Card style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Today’s schedule</Text>
          {data.schedule.length === 0 ? <Text style={{ color: colors.textMuted }}>No appointments scheduled.</Text> : data.schedule.map((entry, index) => (
            <Text key={field(entry, ['id']) + index} style={{ paddingVertical: 6 }}>{field(entry, ['scheduled_time', 'time'])}  ·  {field(entry, ['patient_name', 'name'])}  ·  {field(entry, ['status'])}</Text>
          ))}
        </Card>
        <Card>
          <Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Live queue</Text>
          {data.queue.length === 0 ? <Text style={{ color: colors.textMuted }}>The queue is clear.</Text> : data.queue.map((entry, index) => (
            <Text key={field(entry, ['id', 'appointment_id']) + index} style={{ paddingVertical: 6 }}>#{field(entry, ['position', 'queue_position'])}  ·  Patient {field(entry, ['patient_id'])}  ·  {field(entry, ['status'])}</Text>
          ))}
        </Card>
        <Button title="Refresh dashboard" variant="secondary" onPress={() => void refresh()} style={{ marginTop: 16 }} />
      </ScrollView>
    </ScreenContainer>
  );
}
