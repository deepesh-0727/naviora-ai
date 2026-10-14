import React, { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useNavigation, type NavigationProp } from '@react-navigation/native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { useDoctorQueue } from '../hooks/useDoctorQueue';
import type { DoctorQueueEntry } from '../hooks/useDoctorQueue';

type DoctorNavigation = NavigationProp<{ PatientDetail: { patientId: string | number } }>;

function display(entry: DoctorQueueEntry, keys: string[]): string {
  for (const key of keys) {
    const value = entry[key];
    if (typeof value === 'string' || typeof value === 'number') return String(value);
  }
  return '—';
}

export default function DoctorQueue() {
  const navigation = useNavigation<DoctorNavigation>();
  const { queue, loading, error, backendUnavailable, empty, refresh } = useDoctorQueue();
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const updateEntry = async (entry: DoctorQueueEntry, action: 'status' | 'no-show' | 'up') => {
    const id = display(entry, ['id', 'appointment_id']);
    if (id === '—') return;
    setBusyId(id);
    setActionError(null);
    try {
      if (action === 'status') {
        await apiClient.put(buildApiUrl('doctor', `/queue/${encodeURIComponent(id)}/status`), { status: 'in_room' });
      } else if (action === 'no-show') {
        await apiClient.post(buildApiUrl('doctor', `/queue/${encodeURIComponent(id)}/no-show`));
      } else {
        const ordered = queue.map((item) => display(item, ['id', 'appointment_id']));
        const index = ordered.indexOf(id);
        if (index > 0) [ordered[index - 1], ordered[index]] = [ordered[index], ordered[index - 1]];
        await apiClient.put(buildApiUrl('doctor', '/queue/reorder'), { appointment_ids: ordered.map(Number) });
      }
      await refresh();
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason
        ? (reason as { response?: { status?: number } }).response?.status
        : undefined;
      setActionError(status === 404 || status === 501 ? 'This queue action is not available on the backend yet.' : 'Could not update the queue. Retry the action.');
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <Loader message="Loading queue…" />;
  if (backendUnavailable) return <ScreenContainer><BackendNotAvailable endpoint="GET /staff/doctor/queue" /><Button title="Retry" variant="secondary" onPress={() => void refresh()} /></ScreenContainer>;
  if (error) return <ErrorState message={error} onRetry={() => void refresh()} />;

  return (
    <ScreenContainer>
      <SectionHeader title="Doctor Queue" />
      {actionError ? <Card style={{ marginBottom: 12 }}><Text style={{ color: '#B42318' }}>{actionError}</Text><Button title="Dismiss" variant="secondary" onPress={() => setActionError(null)} /></Card> : null}
      {empty ? <EmptyState message="No patients are waiting." /> : (
        <ScrollView contentContainerStyle={{ paddingBottom: 20 }}>
          {queue.map((entry, index) => {
            const id = display(entry, ['id', 'appointment_id']);
            return (
              <Card key={`${id}-${index}`} style={{ marginBottom: 10 }}>
                <Text style={{ fontWeight: '700', fontSize: 16 }}>#{display(entry, ['position', 'queue_position'])} · Patient {display(entry, ['patient_id'])}</Text>
                <Text style={{ color: '#5F6975', marginVertical: 8 }}>Status: {display(entry, ['status'])} · Priority: {display(entry, ['priority'])}</Text>
                <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
                  <Button title="Move up" variant="secondary" disabled={busyId === id || index === 0} onPress={() => void updateEntry(entry, 'up')} />
                  <Button title="View patient" variant="secondary" onPress={() => navigation.navigate('PatientDetail', { patientId: display(entry, ['patient_id']) })} />
                  <Button title="In room" disabled={busyId === id} onPress={() => void updateEntry(entry, 'status')} />
                  <Button title="No-show" variant="danger" disabled={busyId === id} onPress={() => void updateEntry(entry, 'no-show')} />
                </View>
              </Card>
            );
          })}
        </ScrollView>
      )}
      <Button title="Refresh queue" variant="secondary" onPress={() => void refresh()} />
    </ScreenContainer>
  );
}
