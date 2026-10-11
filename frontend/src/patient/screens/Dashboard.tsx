import React, { useCallback, useEffect, useState } from 'react';
import {
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type { StackNavigationProp } from '@react-navigation/stack';
import type { PatientRootParamList } from '../navigator/PatientNavigator';
import { useNavigation } from '@react-navigation/native';

import { api, type PatientProfile, type PatientNotification } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';
import { useQueue } from '../hooks/useQueue';
import {
  BackendNotAvailable,
  Card,
  EmptyState,
  ErrorState,
  Loader,
  SectionHeader,
  Badge,
} from '../../shared/components';

type Nav = StackNavigationProp<PatientRootParamList>;

const QUICK_ACTIONS = [
  { label: 'Book\nAppointment', icon: '📅', tab: 'Appointments' },
  { label: 'Navigation', icon: '🗺️', screen: 'Navigation' },
  { label: 'Emergency', icon: '🚨', screen: 'Emergency' },
  { label: 'Voice\nAssistant', icon: '🎙️', tab: 'Voice' },
] as const;

function statusColor(status: string): string {
  if (status === 'confirmed') return '#1D8A6C';
  if (status === 'pending') return '#E8A838';
  if (status === 'cancelled') return '#D94A4A';
  return '#8899AA';
}

export default function DashboardScreen() {
  const navigation = useNavigation<Nav>();

  const { appointments, loading: queueLoading, error: queueError, backendUnavailable: queueUnavailable, refresh } = useQueue();

  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileUnavailable, setProfileUnavailable] = useState(false);

  const [recentNotifs, setRecentNotifs] = useState<PatientNotification[]>([]);
  const [notifsUnavailable, setNotifsUnavailable] = useState(false);

  const fetchProfile = useCallback(async () => {
    setProfileLoading(true);
    setProfileUnavailable(false);
    try {
      const res = await api.patient.getProfile();
      setProfile(res.data);
    } catch (err: unknown) {
      const s = (err as { response?: { status?: number } }).response?.status;
      if (s === 404 || s === 501) setProfileUnavailable(true);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  const fetchNotifs = useCallback(async () => {
    try {
      const res = await api.patient.getNotifications({ limit: 5 });
      setRecentNotifs(Array.isArray(res.data) ? res.data.slice(0, 5) : []);
    } catch (err: unknown) {
      const s = (err as { response?: { status?: number } }).response?.status;
      if (s === 404 || s === 501) setNotifsUnavailable(true);
    }
  }, []);

  const refreshAll = useCallback(() => {
    refresh();
    void fetchProfile();
    void fetchNotifs();
  }, [refresh, fetchProfile, fetchNotifs]);

  useEffect(() => {
    void fetchProfile();
    void fetchNotifs();
    void websocketClient.connect();

    const unsubN = websocketClient.subscribe('notification_new', () => {
      void fetchNotifs();
    });
    return () => {
      unsubN();
    };
  }, [fetchProfile, fetchNotifs]);

  const nextAppt = appointments[0] ?? null;
  const displayName = profile
    ? `${profile.first_name} ${profile.last_name}`
    : profileLoading
    ? '…'
    : 'Patient';

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={queueLoading || profileLoading} onRefresh={refreshAll} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Good day 👋</Text>
            <Text style={styles.name}>{displayName}</Text>
          </View>
          <TouchableOpacity
            style={styles.notifBell}
            onPress={() => (navigation as unknown as { navigate: (s: string) => void }).navigate('Notifications')}
            accessibilityLabel="Notifications"
          >
            <Text style={{ fontSize: 22 }}>🔔</Text>
            {recentNotifs.some((n) => !n.is_read) && <View style={styles.notifDot} />}
          </TouchableOpacity>
        </View>

        {/* Next appointment card */}
        <SectionHeader title="Next Appointment" />
        {queueUnavailable ? (
          <BackendNotAvailable endpoint="GET /appointments?upcoming=true" />
        ) : queueLoading ? (
          <Loader message="Loading appointments…" />
        ) : queueError ? (
          <ErrorState message={queueError} onRetry={refresh} />
        ) : nextAppt ? (
          <Card style={styles.apptCard}>
            <View style={styles.apptRow}>
              <Text style={styles.apptIcon}>🏥</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.apptDoctor}>{nextAppt.doctor_name}</Text>
                <Text style={styles.apptDept}>{nextAppt.department_name}</Text>
                <Text style={styles.apptTime}>
                  {new Date(nextAppt.scheduled_time).toLocaleString()}
                </Text>
              </View>
              <Badge label={nextAppt.status} color={statusColor(nextAppt.status)} />
            </View>
            {nextAppt.queue_position > 0 && (
              <View style={styles.queueRow}>
                <Text style={styles.queueLabel}>Queue position</Text>
                <Text style={styles.queueValue}>#{nextAppt.queue_position}</Text>
                <Text style={styles.queueWait}>~{nextAppt.estimated_wait_minutes} min</Text>
              </View>
            )}
          </Card>
        ) : (
          <EmptyState message="No upcoming appointments" />
        )}

        {/* Quick actions */}
        <SectionHeader title="Quick Actions" />
        <View style={styles.quickGrid}>
          {QUICK_ACTIONS.map((action) => (
            <TouchableOpacity
              key={action.label}
              style={styles.quickItem}
              accessibilityLabel={action.label.replace('\n', ' ')}
              onPress={() => {
                if ('screen' in action) {
                  navigation.navigate(action.screen as keyof PatientRootParamList);
                } else {
                  (navigation as unknown as { navigate: (s: string) => void }).navigate(action.tab);
                }
              }}
            >
              <Text style={styles.quickIcon}>{action.icon}</Text>
              <Text style={styles.quickLabel}>{action.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Health summary */}
        {profileUnavailable ? (
          <BackendNotAvailable endpoint="GET /patients/profile" />
        ) : profile ? (
          <>
            <SectionHeader title="Health Summary" />
            <Card>
              <View style={styles.healthRow}>
                <HealthChip icon="🩸" label={profile.blood_group ?? '—'} title="Blood Group" />
                <HealthChip icon="⚕️" label={profile.allergies?.join(', ') || 'None'} title="Allergies" />
              </View>
            </Card>
          </>
        ) : null}

        {/* Recent notifications */}
        <SectionHeader title="Recent Notifications" />
        {notifsUnavailable ? (
          <BackendNotAvailable endpoint="GET /notifications?limit=5" />
        ) : recentNotifs.length === 0 ? (
          <EmptyState message="No recent notifications" />
        ) : (
          recentNotifs.map((n) => (
            <Card key={n.id} style={[styles.notifCard, !n.is_read && styles.notifUnread]}>
              <Text style={styles.notifTitle}>{n.title ?? 'Notification'}</Text>
              <Text style={styles.notifBody}>{n.message ?? n.body ?? ''}</Text>
            </Card>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function HealthChip({ icon, label, title }: { icon: string; label: string; title: string }) {
  return (
    <View style={styles.healthChip}>
      <Text style={styles.healthIcon}>{icon}</Text>
      <Text style={styles.healthTitle}>{title}</Text>
      <Text style={styles.healthValue}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F7F9FC' },
  scroll: { padding: 16, paddingBottom: 100 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  greeting: { fontSize: 14, color: '#5F6975' },
  name: { fontSize: 22, fontWeight: '800', color: '#1C1F24' },
  notifBell: { position: 'relative', padding: 4 },
  notifDot: { position: 'absolute', top: 2, right: 2, width: 8, height: 8, borderRadius: 4, backgroundColor: '#D94A4A' },
  apptCard: { marginBottom: 4 },
  apptRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  apptIcon: { fontSize: 28 },
  apptDoctor: { fontSize: 16, fontWeight: '700', color: '#1C1F24' },
  apptDept: { fontSize: 13, color: '#5F6975' },
  apptTime: { fontSize: 12, color: '#8899AA', marginTop: 2 },
  queueRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderColor: '#E5EAF0' },
  queueLabel: { fontSize: 12, color: '#5F6975', flex: 1 },
  queueValue: { fontSize: 18, fontWeight: '800', color: '#1D8A6C' },
  queueWait: { fontSize: 12, color: '#8899AA' },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 20 },
  quickItem: { width: '46%', backgroundColor: '#fff', borderRadius: 16, padding: 16, alignItems: 'center', borderWidth: 1, borderColor: '#E5EAF0' },
  quickIcon: { fontSize: 28, marginBottom: 8 },
  quickLabel: { fontSize: 12, color: '#1C1F24', fontWeight: '600', textAlign: 'center' },
  healthRow: { flexDirection: 'row', gap: 16 },
  healthChip: { flex: 1, alignItems: 'center' },
  healthIcon: { fontSize: 24, marginBottom: 4 },
  healthTitle: { fontSize: 11, color: '#8899AA', marginBottom: 2 },
  healthValue: { fontSize: 13, fontWeight: '700', color: '#1C1F24', textAlign: 'center' },
  notifCard: { marginBottom: 8 },
  notifUnread: { borderLeftWidth: 3, borderLeftColor: '#1D8A6C' },
  notifTitle: { fontSize: 14, fontWeight: '700', color: '#1C1F24' },
  notifBody: { fontSize: 13, color: '#5F6975', marginTop: 2 },
});
