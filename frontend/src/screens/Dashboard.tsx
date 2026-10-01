import React, { useMemo, useState, useEffect } from 'react';
import {
  StyleSheet,
  View,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  Dimensions,
  ActivityIndicator,
  StatusBar as RNStatusBar,
  Image,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInDown, FadeInRight } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { useQueue } from '../context/QueueContext';
import { useProfile } from '../context/ProfileContext';
import { NavioraText, GlassCard, StatusBadge } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';
import CONFIG from '../../config';

const { width } = Dimensions.get('window');

export default function DashboardScreen({ navigation }: any) {
  const theme = useTheme();
  const { queueData, setQueueData } = useQueue();
  const { profile } = useProfile();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [appointments, setAppointments] = useState<any[]>([]);

  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      const [queueRes, aptsRes] = await Promise.all([
        apiService.get<any>('/appointments/queue'),
        apiService.get<any[]>('/appointments')
      ]);

      if (isMounted) {
        setLoading(false);
        if (queueRes.data && queueRes.data.queue) {
          const userAptInQueue = queueRes.data.queue[0];
          setQueueData({
            position: userAptInQueue?.position || (queueRes.data.total_waiting ? queueRes.data.total_waiting : 0),
            estimatedWait: queueRes.data.average_wait_minutes || 0,
            status: userAptInQueue?.status || 'scheduled',
            doctorName: userAptInQueue?.doctor_name || 'Attending Physician'
          });
        }

        if (aptsRes.data) {
          setAppointments(aptsRes.data);
        }
      }
    };

    fetchData();

    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${CONFIG.WS_BASE_URL}/queue`);
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.position && isMounted) {
            setQueueData({
              position: payload.position,
              estimatedWait: payload.estimated_wait || 15,
              status: payload.status || 'in_progress',
              doctorName: payload.doctor_name || 'Attending Doctor'
            });
          }
        } catch (e) {
          // Parse error silent fallback
        }
      };
    } catch (e) {
      // WS connection fallback
    }

    return () => {
      isMounted = false;
      if (ws) ws.close();
    };
  }, []);

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    return "Good Evening";
  }, []);

  const nextAppointment = appointments.length > 0 ? appointments[0] : null;

  const StatsCard = ({ title, value, icon, color, delay }: any) => (
    <Animated.View entering={FadeInRight.delay(delay).duration(600)}>
      <GlassCard style={styles.statsCard}>
        <View style={[styles.statsIcon, { backgroundColor: color + '20' }]}>
          <Ionicons name={icon} size={24} color={color} />
        </View>
        <NavioraText type="h1" style={{ color }}>{value}</NavioraText>
        <NavioraText type="xs" color="low">{title.toUpperCase()}</NavioraText>
      </GlassCard>
    </Animated.View>
  );

  const ActionItem = ({ title, icon, color, gradient, onPress }: any) => (
    <TouchableOpacity
      activeOpacity={0.9}
      onPress={onPress}
      style={styles.actionItem}
    >
      <LinearGradient colors={gradient} style={styles.actionGradient}>
        <Ionicons name={icon} size={32} color="#FFF" />
        <NavioraText type="label" style={{ color: '#FFF', marginTop: 12 }}>{title}</NavioraText>
      </LinearGradient>
    </TouchableOpacity>
  );

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <StatusBar style="light" />
      
      <LinearGradient colors={theme.colors.gradients.primary} style={styles.header}>
        <SafeAreaView style={styles.headerSafe}>
          <View style={styles.headerContent}>
            <View style={styles.headerLeft}>
              <View style={styles.avatarWrapper}>
                <Image source={{ uri: 'https://i.pravatar.cc/150?u=patient' }} style={styles.avatar} />
                <View style={[styles.onlineDot, { backgroundColor: theme.colors.status.live }]} />
              </View>
              <View style={{ marginLeft: 12 }}>
                <NavioraText type="label" color="low">{greeting},</NavioraText>
                <NavioraText type="h2">{profile?.name || 'Patient'}</NavioraText>
                <NavioraText type="xs" color="low">ID: NAVIORA-{profile?.id || 'USER'}</NavioraText>
              </View>
            </View>
            <TouchableOpacity style={styles.headerBtn} onPress={() => navigation.navigate('Alerts')}>
              <Ionicons name="notifications-outline" size={24} color="#FFF" />
              <View style={[styles.badgeDot, { backgroundColor: theme.colors.error }]} />
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </LinearGradient>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.statsRow}>
          <StatsCard title="Appointments" value={appointments.length} icon="calendar" color={theme.colors.primary} delay={200} />
          <StatsCard title="Queue Pos" value={queueData?.position ? `#${queueData.position}` : '-'} icon="people" color={theme.colors.accent} delay={400} />
          <StatsCard title="Est. Wait" value={queueData?.estimatedWait ? `${queueData.estimatedWait}m` : '0m'} icon="time" color={theme.colors.purple} delay={600} />
        </ScrollView>

        <NavioraText type="label" color="low" style={styles.sectionTitle}>QUICK ACTIONS</NavioraText>
        <View style={styles.grid}>
          <ActionItem
            title="Voice Assistant"
            icon="mic"
            gradient={theme.colors.gradients.primary}
            onPress={() => navigation.navigate('Voice')}
          />
          <ActionItem
            title="Appointments"
            icon="calendar"
            gradient={theme.colors.gradients.accent}
            onPress={() => navigation.navigate('Calendar')}
          />
          <ActionItem
            title="Indoor Map"
            icon="navigate"
            gradient={['#8B5CF6', '#6D28D9']}
            onPress={() => navigation.navigate('Navigation')}
          />
          <ActionItem
            title="Pharmacy"
            icon="medical"
            gradient={['#F59E0B', '#D97706']}
            onPress={() => navigation.navigate('Pharmacy')}
          />
        </View>

        <View style={styles.sectionHeader}>
          <NavioraText type="label" color="low" style={styles.sectionTitle}>TODAY'S SCHEDULE</NavioraText>
          <TouchableOpacity onPress={() => navigation.navigate('Calendar')}>
            <NavioraText type="label" color="primary">See All</NavioraText>
          </TouchableOpacity>
        </View>

        <Animated.View entering={FadeInDown.delay(800).duration(800)}>
          {loading ? (
            <ActivityIndicator color={theme.colors.primary} size="large" style={{ marginVertical: 20 }} />
          ) : nextAppointment ? (
            <GlassCard style={styles.scheduleCard}>
              <View style={styles.scheduleTop}>
                <Image source={{ uri: 'https://i.pravatar.cc/150?u=dr' }} style={styles.doctorAvatar} />
                <View style={{ marginLeft: 12, flex: 1 }}>
                  <NavioraText type="h3">{nextAppointment.doctor_name || 'Doctor'}</NavioraText>
                  <NavioraText type="xs" color="low">{nextAppointment.department_name || 'General'}</NavioraText>
                </View>
                <StatusBadge text={nextAppointment.status || 'Scheduled'} color="primary" />
              </View>
              <View style={[styles.divider, { backgroundColor: theme.colors.glass.border }]} />
              <View style={styles.scheduleBottom}>
                <View style={styles.scheduleInfo}>
                  <Ionicons name="time-outline" size={16} color={theme.colors.text.low} />
                  <NavioraText type="xs" color="low" style={{ marginLeft: 4 }}>
                    {new Date(nextAppointment.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </NavioraText>
                </View>
                <View style={styles.scheduleInfo}>
                  <Ionicons name="people-outline" size={16} color={theme.colors.text.low} />
                  <NavioraText type="xs" color="low" style={{ marginLeft: 4 }}>
                    Queue Position: #{nextAppointment.queue_position || queueData?.position || 1}
                  </NavioraText>
                </View>
              </View>
            </GlassCard>
          ) : (
            <GlassCard style={styles.scheduleCard}>
              <NavioraText type="body" color="low" style={{ textAlign: 'center', paddingVertical: 10 }}>
                No active appointments scheduled for today.
              </NavioraText>
            </GlassCard>
          )}
        </Animated.View>

        <GlassCard style={styles.tipCard}>
          <View style={[styles.tipIcon, { backgroundColor: theme.colors.warning + '20' }]}>
            <Ionicons name="bulb" size={24} color={theme.colors.warning} />
          </View>
          <View style={{ flex: 1, marginLeft: 16 }}>
            <NavioraText type="label" color="warning">HEALTH TIP</NavioraText>
            <NavioraText type="body">Stay hydrated! Aim for at least 8 glasses of water today to maintain optimal health.</NavioraText>
          </View>
        </GlassCard>

        <View style={{ height: 120 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { borderBottomLeftRadius: 32, borderBottomRightRadius: 32, paddingBottom: 24 },
  headerSafe: { paddingTop: RNStatusBar.currentHeight || 44 },
  headerContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 24 },
  headerLeft: { flexDirection: 'row', alignItems: 'center' },
  avatarWrapper: { position: 'relative' },
  avatar: { width: 56, height: 56, borderRadius: 28, borderWidth: 2, borderColor: 'rgba(255,255,255,0.2)' },
  onlineDot: { position: 'absolute', bottom: 0, right: 0, width: 14, height: 14, borderRadius: 7, borderWidth: 2, borderColor: '#0A1628' },
  headerBtn: { width: 48, height: 48, borderRadius: 24, backgroundColor: 'rgba(255,255,255,0.1)', justifyContent: 'center', alignItems: 'center' },
  badgeDot: { position: 'absolute', top: 12, right: 12, width: 8, height: 8, borderRadius: 4 },
  scrollContent: { padding: 24 },
  statsRow: { gap: 16, marginBottom: 32 },
  statsCard: { width: 140, alignItems: 'center', paddingVertical: 20 },
  statsIcon: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center', marginBottom: 12 },
  sectionTitle: { letterSpacing: 1.5, marginBottom: 16, fontWeight: '800' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 16, marginBottom: 32 },
  actionItem: { width: (width - 64) / 2, height: 120, borderRadius: 24, overflow: 'hidden' },
  actionGradient: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  scheduleCard: { padding: 20, marginBottom: 20 },
  scheduleTop: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  doctorAvatar: { width: 48, height: 48, borderRadius: 24 },
  divider: { height: 1, marginVertical: 12 },
  scheduleBottom: { flexDirection: 'row', justifyContent: 'space-between' },
  scheduleInfo: { flexDirection: 'row', alignItems: 'center' },
  tipCard: { flexDirection: 'row', alignItems: 'center', padding: 20, borderLeftWidth: 4, borderLeftColor: '#F59E0B' },
  tipIcon: { width: 48, height: 48, borderRadius: 24, justifyContent: 'center', alignItems: 'center' },
});
