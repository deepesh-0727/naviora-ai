import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import { NavioraText, GlassCard, NavioraStatCard, NavioraHeader } from '../../components/common/AtomicComponents';
import { apiService } from '../../services/api';

interface QueueEntry {
  appointment_id: number;
  doctor_id: number;
  position: number;
  status: string;
}

interface QueueResponse {
  total_waiting: number;
  average_wait_minutes: number;
  queue: QueueEntry[];
}

const statusColor = (status: string) => status === 'in_progress' ? '#10B981' : status === 'scheduled' ? '#F59E0B' : '#6B7280';

export default function DoctorDashboardScreen({ navigation }: any) {
  const theme = useTheme();
  const { user } = useAuth();
  const [queue, setQueue] = useState<QueueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const [greeting] = useState(() => {
    const h = new Date().getHours();
    return h < 12 ? 'Good Morning' : h < 18 ? 'Good Afternoon' : 'Good Evening';
  });

  const loadQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.get<QueueResponse>('/appointments/queue');
      if (!mounted.current) return;
      if (result.error || !result.data) {
        setError(result.error || 'Queue data is unavailable.');
        return;
      }
      setQueue(result.data);
    } catch (loadError) {
      if (mounted.current) {
        setError(loadError instanceof Error ? loadError.message : 'Unable to load the queue.');
      }
    } finally {
      if (mounted.current) setLoading(false);
    }
  };

  useEffect(() => {
    mounted.current = true;
    void loadQueue();
    return () => {
      mounted.current = false;
    };
  }, []);

  const initials = (user?.name || 'Doctor')
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        {/* Header */}
        <LinearGradient colors={theme.colors.gradients.primary} style={styles.headerGrad}>
          <View style={styles.headerRow}>
            <View>
              <NavioraText type="caption" color="inverse" style={{ opacity: 0.75 }}>{greeting}</NavioraText>
              <NavioraText type="h2" color="inverse">{user?.name || 'Doctor'}</NavioraText>
              <View style={styles.badgeRow}>
                <NavioraText type="xs" color="inverse" style={{ opacity: 0.8 }}>
                  {user?.role ? `${user.role[0].toUpperCase()}${user.role.slice(1)} account` : 'Doctor account'}
                </NavioraText>
              </View>
            </View>
            <TouchableOpacity style={styles.avatarBtn}>
              <View style={styles.avatar}>
                <NavioraText type="h3" color="inverse">{initials}</NavioraText>
              </View>
            </TouchableOpacity>
          </View>
        </LinearGradient>

        {/* Stats */}
        <View style={styles.statsRow}>
          <NavioraStatCard icon="people" value={queue?.total_waiting ?? '—'} label="All Queues" tone="sage" />
          <NavioraStatCard icon="time" value={queue ? `${queue.average_wait_minutes}m` : '—'} label="Avg. Wait" tone="sage" />
          <NavioraStatCard icon="list" value={queue?.queue[0] ? `#${queue.queue[0].position}` : '—'} label="First Position" tone="sage" />
        </View>

        {/* Quick Actions */}
        <GlassCard style={styles.card}>
          <NavioraText type="h3" style={{ marginBottom: 16 }}>Quick Actions</NavioraText>
          <View style={styles.actionsGrid}>
            {[
              { icon: 'list', label: 'View Queue', screen: 'DocQueue', color: '#3B82F6' },
              { icon: 'document-text', label: 'Prescriptions', screen: 'WritePrescription', color: '#10B981' },
              { icon: 'warning', label: 'Emergency', screen: 'DoctorEmergency', color: '#DC2626' },
              { icon: 'analytics', label: 'Analytics', screen: 'DocAnalytics', color: '#8B5CF6' },
            ].map((a) => (
              <TouchableOpacity
                key={a.label}
                style={[styles.actionBtn, { backgroundColor: a.color + '12', borderColor: a.color + '30' }]}
                onPress={() => navigation.navigate(a.screen)}
              >
                <Ionicons name={a.icon as any} size={26} color={a.color} />
                <NavioraText type="xs" style={{ color: a.color, marginTop: 6, textAlign: 'center' }}>{a.label}</NavioraText>
              </TouchableOpacity>
            ))}
          </View>
        </GlassCard>

        {/* Queue entries */}
        <GlassCard style={styles.card}>
          <View style={styles.sectionHeader}>
            <NavioraText type="h3">Current Queue</NavioraText>
            <TouchableOpacity onPress={() => navigation.navigate('DocQueue')}>
              <NavioraText type="label" color="primary">See All</NavioraText>
            </TouchableOpacity>
          </View>
          {loading ? (
            <ActivityIndicator color={theme.colors.primary} style={{ paddingVertical: 20 }} />
          ) : error ? (
            <View style={styles.queueMessage}>
              <NavioraText type="caption" color="error">{error}</NavioraText>
              <TouchableOpacity onPress={() => void loadQueue()}>
                <NavioraText type="label" color="primary" style={{ marginTop: 8 }}>Try again</NavioraText>
              </TouchableOpacity>
            </View>
          ) : queue?.queue.length ? (
            queue.queue.slice(0, 4).map((entry) => (
              <TouchableOpacity
                key={entry.appointment_id}
                style={styles.aptRow}
                onPress={() => navigation.navigate('PatientDetails', { patient: entry })}
              >
                <View style={[styles.aptAvatar, { backgroundColor: theme.colors.primaryLight }]}>
                  <NavioraText type="label" color="primary">#{entry.position}</NavioraText>
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <NavioraText type="body">Appointment #{entry.appointment_id}</NavioraText>
                  <NavioraText type="caption" color="low">Queue position {entry.position}</NavioraText>
                </View>
                <View style={[styles.statusChip, { backgroundColor: statusColor(entry.status) + '20' }]}>
                  <NavioraText type="xs" style={{ color: statusColor(entry.status) }}>{entry.status}</NavioraText>
                </View>
              </TouchableOpacity>
            ))
          ) : (
            <NavioraText type="caption" color="low" style={styles.queueMessage}>No patients are currently waiting.</NavioraText>
          )}
        </GlassCard>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingBottom: 100 },
  headerGrad: { padding: 24, paddingBottom: 32, borderBottomLeftRadius: 28, borderBottomRightRadius: 28 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  badgeRow: { flexDirection: 'row', alignItems: 'center', marginTop: 6, gap: 6 },
  avatarBtn: { marginTop: 4 },
  avatar: { width: 52, height: 52, borderRadius: 26, backgroundColor: 'rgba(255,255,255,0.2)', justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: 'rgba(255,255,255,0.4)' },
  statsRow: { flexDirection: 'row', gap: 10, padding: 16, marginTop: -16 },
  card: { margin: 16, marginTop: 0, padding: 16 },
  actionsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  actionBtn: { width: '46%', alignItems: 'center', padding: 16, borderRadius: 16, borderWidth: 1 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  queueMessage: { paddingVertical: 16 },
  aptRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#E5E7EB' },
  aptAvatar: { width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center' },
  statusChip: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
});
