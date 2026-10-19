import React, { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { Ionicons } from '@expo/vector-icons';
import {
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, type PatientNotification } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';
import type { PatientRootParamList } from '../navigator/PatientNavigator';
import { colors } from '../../shared/theme/colors';
import {
  BackendNotAvailable,
  Card,
  ErrorState,
  Loader,
  SectionHeader,
} from '../../shared/components';

type FilterKey = 'all' | 'unread' | 'read';
type PatientNavigation = StackNavigationProp<PatientRootParamList>;

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: 'All Alerts' },
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

  const markAllRead = useCallback(async () => {
    const unread = notifs.filter((item) => !item.is_read);
    try {
      await Promise.all(unread.map((item) => api.patient.markNotificationRead(item.id)));
      setNotifs((previous) => previous.map((item) => ({ ...item, is_read: true })));
    } catch {
      Alert.alert('Could not update alerts', 'Please try again.');
    }
  }, [notifs]);

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
      <View style={styles.headingRow}><View><Text style={styles.heading}>Hospital Alerts</Text><Text style={styles.subtitle}>Live queue, emergency and test notifications</Text></View><TouchableOpacity style={styles.markAll} onPress={() => void markAllRead()} disabled={!notifs.some((item) => !item.is_read)}><Ionicons name="checkmark-done-outline" size={17} color={colors.primary} /><Text style={styles.markAllText}>Mark Read</Text></TouchableOpacity></View>
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
          {filtered.length === 0 && <View style={styles.emptyState}><Ionicons name="notifications-off-outline" size={48} color={colors.textMuted} /><Text style={styles.emptyTitle}>All Caught Up</Text><Text style={styles.emptyText}>You have no new alerts in this category. Live appointment queue updates will appear here.</Text></View>}
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
  safe: { flex: 1, backgroundColor: colors.background },
  headingRow: { paddingHorizontal: 16, paddingTop: 10, paddingBottom: 4, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  heading: { color: colors.text, fontSize: 22, fontWeight: '800' },
  subtitle: { color: colors.textMuted, fontSize: 13, marginTop: 3, maxWidth: 215 },
  markAll: { backgroundColor: colors.white, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 9, flexDirection: 'row', alignItems: 'center', gap: 5 },
  markAllText: { color: colors.primary, fontSize: 12, fontWeight: '700' },
  filterRow: { flexDirection: 'row', padding: 16, gap: 8 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontSize: 13, color: colors.textMuted, fontWeight: '600' },
  chipTextActive: { color: colors.white },
  scroll: { paddingHorizontal: 16, paddingBottom: 100 },
  notifCard: { marginBottom: 8 },
  notifUnread: { borderLeftWidth: 3, borderLeftColor: colors.primary },
  notifRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  notifTitle: { fontSize: 14, fontWeight: '700', color: colors.text },
  notifBody: { fontSize: 13, color: colors.textMuted, marginTop: 2 },
  notifTime: { fontSize: 11, color: colors.textMuted, marginTop: 4 },
  notifActions: { gap: 6 },
  actionBtn: { padding: 4 },
  feedbackButton: { alignSelf: 'flex-start', backgroundColor: colors.primary, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8, marginTop: 8 },
  feedbackButtonText: { color: colors.white, fontWeight: '700', fontSize: 12 },
  emptyState: { margin: 16, minHeight: 220, padding: 22, borderRadius: 20, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  emptyTitle: { color: colors.text, fontSize: 18, fontWeight: '800', marginTop: 14 },
  emptyText: { color: colors.textMuted, textAlign: 'center', marginTop: 6, lineHeight: 20 },
});
