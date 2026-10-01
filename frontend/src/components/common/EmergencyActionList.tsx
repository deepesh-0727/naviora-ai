import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { NavioraBadge, NavioraButton, NavioraCard, NavioraText } from './AtomicComponents';
import { apiService } from '../../services/api';

interface EmergencyItem {
  id: number;
  status: string;
  priority: string;
  location: string;
  description?: string | null;
  assigned_staff?: { primary_staff_id?: number };
  arrival_time?: string | null;
}

interface EmergencyResponse {
  items: EmergencyItem[];
}

interface CurrentUser {
  id: number;
}

export default function EmergencyActionList() {
  const [items, setItems] = useState<EmergencyItem[]>([]);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingAction, setSavingAction] = useState<{ id: number; action: 'respond' | 'arrived' | 'resolve' } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [result, userResult] = await Promise.all([
        apiService.get<EmergencyResponse>('/emergency/active'),
        apiService.get<CurrentUser>('/auth/me'),
      ]);
      if (!result.data || !userResult.data) {
        setError(result.error || userResult.error || 'Emergency dispatch data is unavailable.');
        return;
      }
      setItems(Array.isArray(result.data.items) ? result.data.items : []);
      setCurrentUserId(userResult.data.id);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load active emergencies.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const mutate = async (item: EmergencyItem, action: 'respond' | 'arrived' | 'resolve') => {
    setSavingAction({ id: item.id, action });
    setError(null);
    try {
      const result = action === 'respond'
        ? await apiService.post<{ status: string }>(`/emergency/respond/${item.id}`, {})
        : action === 'arrived'
          ? await apiService.put<{ status: string }>(`/emergency/staff-arrived?emergency_id=${item.id}`, {})
          : await apiService.put<{ status: string }>(`/emergency/resolve/${item.id}`, {});
      if (result.error || !result.data) {
        setError(result.error || `Unable to ${action} to emergency #${item.id}.`);
        return;
      }
      await load();
    } catch (mutationError) {
      setError(mutationError instanceof Error ? mutationError.message : `Unable to ${action} to emergency #${item.id}.`);
    } finally {
      setSavingAction(null);
    }
  };

  return (
    <View style={styles.container}>
      <NavioraButton title="Refresh emergencies" variant="secondary" onPress={() => void load()} />
      {loading ? <ActivityIndicator style={styles.loader} /> : null}
      {error ? <NavioraText color="danger" style={styles.message}>{error}</NavioraText> : null}
      {!loading && !error && items.length === 0 ? (
        <NavioraText color="secondary" style={styles.empty}>No active emergencies.</NavioraText>
      ) : null}
      {items.map(item => (
        <NavioraCard key={String(item.id)} style={styles.card}>
          <View style={styles.titleRow}>
            <NavioraText type="body" style={styles.title}>Emergency #{item.id}</NavioraText>
            <NavioraBadge label={item.priority} tone="warning" />
          </View>
          {item.description ? <NavioraText type="caption" style={styles.detail}>{item.description}</NavioraText> : null}
          <NavioraText type="caption" color="secondary" style={styles.detail}>Location: {item.location}</NavioraText>
          <NavioraText type="caption" color="secondary" style={styles.detail}>Status: {item.status}</NavioraText>
          {item.assigned_staff?.primary_staff_id ? (
            <NavioraText type="caption" color="secondary" style={styles.detail}>
              Assigned staff #{item.assigned_staff.primary_staff_id}
            </NavioraText>
          ) : null}
          {item.arrival_time ? (
            <NavioraText type="caption" color="secondary" style={styles.detail}>Responder arrival recorded</NavioraText>
          ) : null}
          {!item.assigned_staff?.primary_staff_id ? (
            <NavioraButton
              title="Respond"
              onPress={() => void mutate(item, 'respond')}
              loading={savingAction?.id === item.id && savingAction.action === 'respond'}
              disabled={savingAction !== null}
              style={styles.action}
            />
          ) : null}
          {item.assigned_staff?.primary_staff_id === currentUserId && !item.arrival_time ? (
            <NavioraButton
              title="Mark arrived"
              variant="secondary"
              onPress={() => void mutate(item, 'arrived')}
              loading={savingAction?.id === item.id && savingAction.action === 'arrived'}
              disabled={savingAction !== null}
              style={styles.action}
            />
          ) : null}
          <NavioraButton
            title="Resolve"
            variant="secondary"
            onPress={() => void mutate(item, 'resolve')}
            loading={savingAction?.id === item.id && savingAction.action === 'resolve'}
            disabled={savingAction !== null}
            style={styles.action}
          />
        </NavioraCard>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingBottom: 24 },
  loader: { marginTop: 24 },
  message: { marginTop: 14 },
  empty: { marginTop: 22 },
  card: { marginTop: 14 },
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontWeight: '700' },
  detail: { marginTop: 8 },
  action: { marginTop: 12 },
});
