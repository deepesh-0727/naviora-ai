import { colors } from '../../shared/theme/colors';
import React, { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useNavigation, type NavigationProp } from '@react-navigation/native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Header, Loader, ScreenContainer, Toast } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { useDoctorQueue } from '../hooks/useDoctorQueue';
import type { DoctorQueueEntry } from '../hooks/useDoctorQueue';

type DoctorNavigation = NavigationProp<{ PatientDetail: { patientId: string | number; appointmentId?: string } }>;

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
  const [actionToast, setActionToast] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<{ appointmentId: string; action: 'in_room' | 'completed' | 'no-show' | 'up' } | null>(null);

  useEffect(() => {
    if (!actionToast) return undefined;
    const timeout = setTimeout(() => setActionToast(null), 4000);
    return () => clearTimeout(timeout);
  }, [actionToast]);

  const updateEntry = async (entry: DoctorQueueEntry, action: 'status' | 'no-show' | 'up', status?: 'in_room' | 'completed') => {
    const id = display(entry, ['id', 'appointment_id']);
    if (id === '—' || pendingAction) return;
    const pendingName = action === 'status' ? status : action;
    if (!pendingName) return;
    setPendingAction({ appointmentId: id, action: pendingName });
    setActionToast(null);
    try {
      if (action === 'status') {
        await apiClient.put(buildApiUrl('doctor', `/queue/${encodeURIComponent(id)}/status`), { status });
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
      const response = typeof reason === 'object' && reason !== null && 'response' in reason
        ? (reason as { response?: { status?: number; data?: { detail?: unknown; message?: unknown } } }).response
        : undefined;
      const detail = response?.data?.detail;
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => typeof item === 'object' && item !== null && 'msg' in item ? String(item.msg) : String(item)).join('; ')
          : typeof response?.data?.message === 'string'
            ? response.data.message
            : response?.status === 401
              ? 'Your session has expired. Please sign in again.'
              : response?.status
                ? `Queue update failed (${response.status}). Please retry.`
                : 'Could not reach the server. Check your connection and retry.';
      setActionToast(message);
    } finally {
      setPendingAction(null);
    }
  };

  if (loading) return <ScreenContainer><Header title="Doctor Queue" /><Loader message="Loading queue…" /></ScreenContainer>;
  if (backendUnavailable) return <ScreenContainer><Header title="Doctor Queue" /><BackendNotAvailable endpoint="GET /staff/doctor/queue" /><Button title="Retry" variant="secondary" onPress={() => void refresh()} /></ScreenContainer>;
  if (error) return <ScreenContainer><Header title="Doctor Queue" /><ErrorState message={error} onRetry={() => void refresh()} /></ScreenContainer>;

  return (
    <ScreenContainer>
      <Header title="Doctor Queue" />
      {actionToast ? <Toast message={actionToast} /> : null}
      {empty ? <EmptyState message="No patients in queue. Enjoy your break!" /> : (
        <ScrollView contentContainerStyle={{ paddingBottom: 100 }}>
          {queue.map((entry, index) => {
            const id = display(entry, ['id', 'appointment_id']);
            return (
              <Card key={`${id}-${index}`} style={{ marginBottom: 10 }}>
                <Text style={{ fontWeight: '700', fontSize: 16 }}>#{display(entry, ['position', 'queue_position'])} · Patient {display(entry, ['patient_id'])}</Text>
                <Text style={{ color: colors.textMuted, marginVertical: 8 }}>Status: {display(entry, ['status'])} · Priority: {display(entry, ['priority'])}</Text>
                <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
                  <Button title="Move up" variant="secondary" disabled={Boolean(pendingAction) || index === 0} onPress={() => void updateEntry(entry, 'up')} />
                  <Button title="View patient" variant="secondary" disabled={Boolean(pendingAction)} onPress={() => navigation.navigate('PatientDetail', { patientId: display(entry, ['patient_id']), appointmentId: id })} />
                  <Button
                    title="Mark In-Room"
                    loading={pendingAction?.appointmentId === id && pendingAction.action === 'in_room'}
                    disabled={Boolean(pendingAction)}
                    onPress={() => void updateEntry(entry, 'status', 'in_room')}
                  />
                  <Button
                    title="Mark Complete"
                    variant="secondary"
                    loading={pendingAction?.appointmentId === id && pendingAction.action === 'completed'}
                    disabled={Boolean(pendingAction)}
                    onPress={() => void updateEntry(entry, 'status', 'completed')}
                  />
                  <Button title="No-show" variant="danger" disabled={Boolean(pendingAction)} onPress={() => void updateEntry(entry, 'no-show')} />
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
