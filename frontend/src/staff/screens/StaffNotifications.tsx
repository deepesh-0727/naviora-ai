import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, Text } from 'react-native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';

type Notification = Record<string, unknown>;
function items(value: unknown): Notification[] {
  if (Array.isArray(value)) return value.filter((entry): entry is Notification => typeof entry === 'object' && entry !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) return value.items.filter((entry): entry is Notification => typeof entry === 'object' && entry !== null);
  return [];
}
function valueOf(entry: Notification, keys: string[]): string {
  for (const key of keys) { const value = entry[key]; if (typeof value === 'string' || typeof value === 'number') return String(value); }
  return '—';
}

export default function StaffNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true); setError(null); setUnavailable(false);
    try {
      const response = await apiClient.get<unknown>(buildApiUrl('doctor', '/notifications'));
      setNotifications(items(response.data));
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      if (status === 404 || status === 501) setUnavailable(true); else setError('Could not load staff notifications.');
    } finally { setLoading(false); }
  }, []);
  useEffect(() => {
    void refresh();
    void websocketClient.connect();
    const unsubscribe = websocketClient.subscribe('notification_new', () => { void refresh(); });
    return unsubscribe;
  }, [refresh]);

  const markRead = async (notification: Notification) => {
    const id = valueOf(notification, ['id', 'notification_id']);
    if (id === '—') { setActionError('This notification has no identifier.'); return; }
    setBusyId(id); setActionError(null);
    try {
      await apiClient.put(buildApiUrl('doctor', `/notifications/${encodeURIComponent(id)}/read`));
      await refresh();
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      setActionError(status === 404 || status === 501 ? 'Marking staff notifications read is not available on the backend yet.' : 'Could not update this notification.');
    } finally { setBusyId(null); }
  };

  if (loading) return <Loader message="Loading notifications…" />;
  if (unavailable) return <ScreenContainer><BackendNotAvailable endpoint="GET /staff/notifications" /><Button title="Retry" variant="secondary" onPress={() => void refresh()} /></ScreenContainer>;
  if (error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  return <ScreenContainer><SectionHeader title="Notifications" />{actionError ? <Text accessibilityRole="alert" style={{ color: '#B42318', marginBottom: 8 }}>{actionError}</Text> : null}{notifications.length === 0 ? <EmptyState message="You have no staff notifications." /> : <ScrollView contentContainerStyle={{ paddingBottom: 16, gap: 10 }}>{notifications.map((item, index) => {
    const id = valueOf(item, ['id', 'notification_id']);
    const isRead = item.is_read === true || item.read === true;
    return <Card key={`${id}-${index}`}><Text style={{ fontWeight: '700' }}>{valueOf(item, ['title', 'subject'])}</Text><Text style={{ marginVertical: 6 }}>{valueOf(item, ['message', 'body'])}</Text><Text style={{ color: '#5F6975', marginBottom: 8 }}>{valueOf(item, ['created_at', 'timestamp'])}</Text>{!isRead ? <Button title={busyId === id ? 'Updating…' : 'Mark as read'} disabled={busyId === id} onPress={() => void markRead(item)} /> : <Text style={{ color: '#5F6975' }}>Read</Text>}</Card>;
  })}</ScrollView>}<Button title="Refresh notifications" variant="secondary" onPress={() => void refresh()} style={{ marginTop: 12 }} /></ScreenContainer>;
}
