import React, { useCallback, useEffect, useState } from 'react';
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
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
  Avatar,
} from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type Nav = StackNavigationProp<PatientRootParamList>;

const QUICK_ACTIONS = [
  { label: 'Voice AI Assistant', description: 'Speak to book, triage symptoms and navigate', icon: 'mic-outline' as const, tab: 'Voice' as const },
  { label: 'Indoor Hospital Map', description: 'Find departments and get directions', icon: 'navigate-outline' as const, screen: 'Navigation' as const },
  { label: 'Book an Appointment', description: 'Browse specialists and available times', icon: 'calendar-outline' as const, tab: 'Appointments' as const },
] as const;

function statusColor(status: string): string {
  if (status === 'confirmed') return colors.primary;
  if (status === 'pending') return colors.accent;
  if (status === 'cancelled') return colors.danger;
  return colors.textMuted;
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

  const greeting = new Date().getHours() < 12 ? 'Good morning,' : new Date().getHours() < 17 ? 'Good afternoon,' : 'Good evening,';
  const queuePosition = nextAppt?.queue_position;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={queueLoading || profileLoading} onRefresh={refreshAll} />}
      >
        {/* Patient identity and alerts */}
        <View style={styles.header}>
          <View style={styles.identity}>
            <Avatar label={displayName} size={48} />
            <View>
              <Text style={styles.greeting}>{greeting}</Text>
              <Text style={styles.name}>{displayName}</Text>
            </View>
          </View>
          <TouchableOpacity
            style={styles.iconButton}
            onPress={() => (navigation as unknown as { navigate: (s: string) => void }).navigate('Notifications')}
            accessibilityLabel="Notifications"
          >
            <Ionicons name="notifications-outline" size={21} color={colors.text} />
            {recentNotifs.some((n) => !n.is_read) && <View style={styles.notifDot} />}
          </TouchableOpacity>
        </View>

        <View style={styles.patientId}><Ionicons name="finger-print-outline" size={18} color={colors.primary} /><Text style={styles.patientIdText}>Patient ID: NAV-{profile?.id ?? '—'}</Text><Text style={styles.secureLabel}>SECURE</Text></View>

        <View style={styles.metricsRow}>
          <Card style={styles.metricCard}><View style={[styles.metricIcon, styles.greenIcon]}><Ionicons name="time-outline" size={20} color={colors.primary} /></View><Text style={styles.metricValue}>{queuePosition ? `#${queuePosition}` : '—'}</Text><Text style={styles.metricLabel}>Queue in line</Text><Text style={styles.metricHint}>{queuePosition ? `~${nextAppt?.estimated_wait_minutes ?? '—'} min wait` : 'No active queue'}</Text></Card>
          <Card style={styles.metricCard}><View style={[styles.metricIcon, styles.amberIcon]}><Ionicons name="calendar-outline" size={20} color={colors.accent} /></View><Text style={[styles.metricValue, { color: colors.accent }]}>{appointments.length}</Text><Text style={styles.metricLabel}>Bookings</Text><Text style={styles.metricHint}>{nextAppt ? new Date(nextAppt.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'No upcoming visit'}</Text></Card>
          <Card style={styles.metricCard}><View style={[styles.metricIcon, styles.redIcon]}><Ionicons name="pulse-outline" size={20} color={colors.danger} /></View><Text style={[styles.metricValue, { color: colors.danger, fontSize: 17 }]}>SOS</Text><Text style={styles.metricLabel}>Response</Text><Text style={[styles.metricHint, styles.ready]}>Ready 24/7</Text></Card>
        </View>

        {/* Next appointment card */}
        <SectionHeader title="Today's Appointment Schedule" />
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
        <SectionHeader title="Hospital Quick Actions" />
        <View style={styles.quickGrid}>
          {QUICK_ACTIONS.map((action) => (
            <TouchableOpacity
              key={action.label}
              style={styles.quickItem}
              accessibilityLabel={action.label.replace('\n', ' ')}
              onPress={() => {
                if ('screen' in action) {
                  navigation.navigate(action.screen);
                } else {
                  (navigation as unknown as { navigate: (s: string) => void }).navigate(action.tab);
                }
              }}
            >
              <View style={styles.quickIconBox}><Ionicons name={action.icon} size={24} color={colors.primary} /></View>
              <Ionicons name="arrow-forward-outline" size={18} color={colors.primary} style={styles.quickArrow} />
              <Text style={styles.quickLabel}>{action.label}</Text>
              <Text style={styles.quickDescription}>{action.description}</Text>
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
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: 16, paddingBottom: 112 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  identity: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  greeting: { fontSize: 14, color: colors.textMuted },
  name: { fontSize: 20, fontWeight: '800', color: colors.text },
  iconButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  notifDot: { position: 'absolute', top: 8, right: 8, width: 8, height: 8, borderRadius: 4, backgroundColor: colors.danger },
  patientId: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: colors.primaryLight, borderWidth: 1, borderColor: colors.primary, borderRadius: 14, padding: 12, marginBottom: 16 },
  patientIdText: { color: colors.primary, fontWeight: '800', flex: 1 },
  secureLabel: { color: colors.primary, fontSize: 10, fontWeight: '800' },
  metricsRow: { flexDirection: 'row', gap: 8, marginBottom: 24 },
  metricCard: { flex: 1, paddingHorizontal: 8, paddingVertical: 12, alignItems: 'center', minHeight: 150 },
  metricIcon: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  greenIcon: { backgroundColor: colors.primaryLight },
  amberIcon: { backgroundColor: colors.amberSoft },
  redIcon: { backgroundColor: colors.dangerLight },
  metricValue: { fontSize: 22, fontWeight: '800', color: colors.primary },
  metricLabel: { color: colors.textMuted, fontSize: 12, textAlign: 'center', marginTop: 2 },
  metricHint: { color: colors.text, fontSize: 11, fontWeight: '600', textAlign: 'center', marginTop: 4 },
  ready: { color: colors.danger },
  apptCard: { marginBottom: 4 },
  apptRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  apptIcon: { fontSize: 28 },
  apptDoctor: { fontSize: 16, fontWeight: '700', color: colors.text },
  apptDept: { fontSize: 13, color: colors.textMuted },
  apptTime: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  queueRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderColor: colors.border },
  queueLabel: { fontSize: 12, color: colors.textMuted, flex: 1 },
  queueValue: { fontSize: 18, fontWeight: '800', color: colors.primary },
  queueWait: { fontSize: 12, color: colors.textMuted },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 20 },
  quickItem: { width: '100%', backgroundColor: colors.white, borderRadius: 18, padding: 16, alignItems: 'flex-start', borderWidth: 1, borderColor: colors.border, marginBottom: 10, minHeight: 150, ...Platform.select({ android: { elevation: 2 }, default: { shadowColor: colors.shadow, shadowOpacity: 0.05, shadowRadius: 8, shadowOffset: { width: 0, height: 3 } } }) },
  quickIconBox: { width: 48, height: 48, borderRadius: 14, backgroundColor: colors.primaryLight, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  quickArrow: { position: 'absolute', top: 18, right: 18 },
  quickLabel: { fontSize: 16, color: colors.text, fontWeight: '700' },
  quickDescription: { fontSize: 13, color: colors.textMuted, marginTop: 4, lineHeight: 19, maxWidth: 250 },
  healthRow: { flexDirection: 'row', gap: 16 },
  healthChip: { flex: 1, alignItems: 'center' },
  healthIcon: { fontSize: 24, marginBottom: 4 },
  healthTitle: { fontSize: 11, color: colors.textMuted, marginBottom: 2 },
  healthValue: { fontSize: 13, fontWeight: '700', color: colors.text, textAlign: 'center' },
  notifCard: { marginBottom: 8 },
  notifUnread: { borderLeftWidth: 3, borderLeftColor: colors.primary },
  notifTitle: { fontSize: 14, fontWeight: '700', color: colors.text },
  notifBody: { fontSize: 13, color: colors.textMuted, marginTop: 2 },
});
