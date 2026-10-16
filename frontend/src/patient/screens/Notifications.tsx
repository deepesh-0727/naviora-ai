import React, { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import {
  Alert,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { api, type PatientNotification } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';
import type { PatientRootParamList } from '../navigator/PatientNavigator';
import {
  BackendNotAvailable,
  Card,
  EmptyState,
  ErrorState,
  Loader,
  SectionHeader,
} from '../../shared/components';

type FilterKey = 'all' | 'unread' | 'read';
type PatientNavigation = StackNavigationProp<PatientRootParamList>;

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'unread', label: 'Unread' },
  { key: 'read', label: 'Read' },
];

function groupNotifs(notifs: PatientNotification[]): { today: PatientNotification[]; yesterday: PatientNotification[]; earlier: PatientNotification[] } {
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startYesterday = startToday - 86400000;

  const today: PatientNotification[] = [];
  const yesterday: PatientNotification[] = [];
  const earlier: PatientNotification[] = [];

  for (const n of notifs) {
    const t = n.created_at ? new Date(n.created_at).getTime() : 0;
    if (t >= startToday) today.push(n);
    else if (t >= startYesterday) yesterday.push(n);
    else earlier.push(n);
  }
  return { today, yesterday, earlier };
}

export default function NotificationsScreen() {
  const navigation = useNavigation<PatientNavigation>();
  const [notifs, setNotifs] = useState<PatientNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);
  const [filter, setFilter] = useState<FilterKey>('all');

  const fetchNotifs = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBackendUnavailable(false);
    try {
      const res = await api.patient.getNotifications();
      setNotifs(Array.isArray(res.data) ? res.data : []);
    } catch (err: unknown) {
      const s = (err as { response?: { status?: number } }).response?.status;
      if (s === 404 || s === 501) {
        setBackendUnavailable(true);
      } else {
        setError('Failed to load notifications.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const markRead = useCallback(async (id: number) => {
    try {
      await api.patient.markNotificationRead(id);
      setNotifs((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    } catch {
      // silently fail — item still shows
    }
  }, []);

  const deleteNotif = useCallback(async (id: number) => {
    Alert.alert('Delete notification?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.patient.deleteNotification(id);
            setNotifs((prev) => prev.filter((n) => n.id !== id));
          } catch {
            Alert.alert('Error', 'Failed to delete notification.');
          }
        },
      },
    ]);
  }, []);

  useEffect(() => {
    void fetchNotifs();
    void websocketClient.connect();
    const unsub = websocketClient.subscribe('notification_new', () => {
      void fetchNotifs();
    });
    return () => {
      unsub();
    };
  }, [fetchNotifs]);

  const filtered = notifs.filter((n) => {
    if (filter === 'unread') return !n.is_read;
    if (filter === 'read') return n.is_read;
    return true;
  });

  const { today, yesterday, earlier } = groupNotifs(filtered);

  if (backendUnavailable) {
    return (
      <SafeAreaView style={styles.safe}>
        <BackendNotAvailable endpoint="GET /notifications" />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[styles.chip, filter === f.key && styles.chipActive]}
            onPress={() => setFilter(f.key)}
            accessibilityLabel={`Filter ${f.label}`}
          >
            <Text style={[styles.chipText, filter === f.key && styles.chipTextActive]}>{f.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <Loader message="Loading notifications…" />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchNotifs} />
      ) : (
        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={fetchNotifs} />}
        >
          {today.length > 0 && (
            <>
              <SectionHeader title="Today" />
              {today.map((n) => <NotifCard key={n.id} item={n} onRead={markRead} onDelete={deleteNotif} onFeedback={(id) => navigation.navigate('Feedback', { appointmentId: id })} />)}
            </>
          )}
          {yesterday.length > 0 && (
            <>
              <SectionHeader title="Yesterday" />
              {yesterday.map((n) => <NotifCard key={n.id} item={n} onRead={markRead} onDelete={deleteNotif} onFeedback={(id) => navigation.navigate('Feedback', { appointmentId: id })} />)}
            </>
          )}
          {earlier.length > 0 && (
            <>
              <SectionHeader title="Earlier" />
              {earlier.map((n) => <NotifCard key={n.id} item={n} onRead={markRead} onDelete={deleteNotif} onFeedback={(id) => navigation.navigate('Feedback', { appointmentId: id })} />)}
            </>
          )}
          {filtered.length === 0 && <EmptyState message="No notifications" />}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

function NotifCard({
  item,
  onRead,
  onDelete,
  onFeedback,
}: {
  item: PatientNotification;
  onRead: (id: number) => void;
  onDelete: (id: number) => void;
  onFeedback: (appointmentId: number) => void;
}) {
  const feedbackAppointmentId = item.data?.type === 'feedback_request' ? Number(item.data.appointment_id) : NaN;
  return (
    <Card style={[styles.notifCard, !item.is_read && styles.notifUnread]}>
      <View style={styles.notifRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.notifTitle}>{item.title ?? 'Notification'}</Text>
          <Text style={styles.notifBody}>{item.message ?? item.body ?? ''}</Text>
          {Number.isInteger(feedbackAppointmentId) && feedbackAppointmentId > 0 ? (
            <TouchableOpacity style={styles.feedbackButton} onPress={() => onFeedback(feedbackAppointmentId)}>
              <Text style={styles.feedbackButtonText}>Share feedback</Text>
            </TouchableOpacity>
          ) : null}
          {item.created_at ? (
            <Text style={styles.notifTime}>{new Date(item.created_at).toLocaleString()}</Text>
          ) : null}
        </View>
        <View style={styles.notifActions}>
          {!item.is_read && (
            <TouchableOpacity
              onPress={() => onRead(item.id)}
              accessibilityLabel="Mark as read"
              style={styles.actionBtn}
            >
              <Text style={{ fontSize: 16 }}>✅</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            onPress={() => onDelete(item.id)}
            accessibilityLabel="Delete notification"
            style={styles.actionBtn}
          >
            <Text style={{ fontSize: 16 }}>🗑️</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F7F9FC' },
  filterRow: { flexDirection: 'row', padding: 16, gap: 8 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999, backgroundColor: '#EEF2F7', borderWidth: 1, borderColor: '#DDE5EE' },
  chipActive: { backgroundColor: '#1D8A6C', borderColor: '#1D8A6C' },
  chipText: { fontSize: 13, color: '#5F6975', fontWeight: '600' },
  chipTextActive: { color: '#fff' },
  scroll: { paddingHorizontal: 16, paddingBottom: 100 },
  notifCard: { marginBottom: 8 },
  notifUnread: { borderLeftWidth: 3, borderLeftColor: '#1D8A6C' },
  notifRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  notifTitle: { fontSize: 14, fontWeight: '700', color: '#1C1F24' },
  notifBody: { fontSize: 13, color: '#5F6975', marginTop: 2 },
  notifTime: { fontSize: 11, color: '#8899AA', marginTop: 4 },
  notifActions: { gap: 6 },
  actionBtn: { padding: 4 },
  feedbackButton: { alignSelf: 'flex-start', backgroundColor: '#1D8A6C', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, marginTop: 8 },
  feedbackButtonText: { color: '#fff', fontWeight: '700', fontSize: 12 },
});
