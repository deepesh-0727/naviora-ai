import React, { useEffect, useState, useCallback } from 'react';
import { StyleSheet, View, ScrollView, TouchableOpacity, SafeAreaView, ActivityIndicator, RefreshControl, Image, Dimensions } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInUp } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { NavioraText, GlassCard, StatusBadge } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';

const { width } = Dimensions.get('window');

interface AppointmentItem {
  id: number;
  doctor_name: string;
  department_name: string;
  scheduled_time: string;
  status: string;
  queue_position: number;
  room?: string;
  avatar?: string;
}

export default function AppointmentScreen({ navigation }: any) {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState('Upcoming');
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAppointments = useCallback(async () => {
    const result = await apiService.get<AppointmentItem[]>('/appointments');
    if (result.data) {
      setAppointments(Array.isArray(result.data) ? result.data : []);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchAppointments().finally(() => setLoading(false));
  }, [fetchAppointments]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchAppointments();
    setRefreshing(false);
  };

  const cancelAppointment = async (id: number) => {
    const result = await apiService.delete(`/appointments/${id}`);
    if (result.status >= 200 && result.status < 300) {
      setAppointments(current => current.map(item => item.id === id ? { ...item, status: 'cancelled' } : item));
    }
  };

  const TabButton = ({ name }: { name: string }) => (
    <TouchableOpacity
      onPress={() => setActiveTab(name)}
      style={[styles.tabBtn, activeTab === name && { borderBottomColor: theme.colors.primary, borderBottomWidth: 3 }]}
    >
      <NavioraText type="label" color={activeTab === name ? 'high' : 'low'}>{name.toUpperCase()}</NavioraText>
    </TouchableOpacity>
  );

  const AppointmentCard = ({ item, index }: { item: AppointmentItem; index: number }) => (
    <Animated.View entering={FadeInUp.delay(index * 100)}>
      <GlassCard style={styles.card}>
        <View style={styles.cardTop}>
          <Image source={{ uri: item.avatar || `https://i.pravatar.cc/150?u=${item.id}` }} style={styles.avatar} />
          <View style={styles.cardMain}>
            <NavioraText type="h3">{item.doctor_name}</NavioraText>
            <NavioraText type="xs" color="low">{item.department_name}{item.room ? ` • Room ${item.room}` : ''}</NavioraText>
          </View>
          <StatusBadge text={item.status} color={item.status === 'scheduled' ? 'primary' : item.status === 'completed' ? 'success' : 'error'} />
        </View>

        <View style={styles.cardDivider} />

        <View style={styles.cardBottom}>
          <View style={styles.infoRow}>
            <Ionicons name="time-outline" size={16} color={theme.colors.text.low} />
            <NavioraText type="label" color="medium" style={{ marginLeft: 6 }}>
              {new Date(item.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </NavioraText>
          </View>
          <View style={styles.infoRow}>
            <Ionicons name="people-outline" size={16} color={theme.colors.text.low} />
            <NavioraText type="label" color="medium" style={{ marginLeft: 6 }}>
              {item.queue_position ? `Pos: #${item.queue_position}` : 'Not queued'}
            </NavioraText>
          </View>
        </View>

        <View style={styles.actionRow}>
          <TouchableOpacity style={[styles.actionBtn, { borderColor: theme.colors.glass.border }]}>
            <NavioraText type="xs" color="low">Reschedule</NavioraText>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.actionBtn, { borderColor: theme.colors.glass.border }]} onPress={() => cancelAppointment(item.id)} disabled={item.status === 'cancelled'}>
            <NavioraText type="xs" color="error">Cancel</NavioraText>
          </TouchableOpacity>
        </View>
      </GlassCard>
    </Animated.View>
  );

  const visibleAppointments = appointments.filter(item => {
    if (activeTab === 'Canceled') return item.status === 'cancelled';
    if (activeTab === 'Past') return ['completed', 'cancelled'].includes(item.status);
    return !['completed', 'cancelled'].includes(item.status);
  });

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.header}>
          <NavioraText type="h2">My Appointments</NavioraText>
          <TouchableOpacity style={styles.iconBtn}>
            <Ionicons name="options-outline" size={24} color="#FFF" />
          </TouchableOpacity>
        </View>

        <View style={styles.tabContainer}>
          <TabButton name="Upcoming" />
          <TabButton name="Past" />
          <TabButton name="Canceled" />
        </View>

        <ScrollView
          contentContainerStyle={styles.scrollContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary} />}
        >
          {loading && !refreshing ? (
            <ActivityIndicator size="large" color={theme.colors.primary} style={{ marginTop: 40 }} />
          ) : visibleAppointments.length > 0 ? (
            visibleAppointments.map((apt, idx) => <AppointmentCard key={apt.id} item={apt} index={idx} />)
          ) : (
            <View style={styles.emptyState}>
              <Ionicons name="calendar-outline" size={80} color={theme.colors.glass.border} />
              <NavioraText type="h3" color="low" style={{ marginTop: 20 }}>No appointments found</NavioraText>
              <NavioraText type="body" color="low" align="center" style={{ marginTop: 8 }}>
                You don't have any appointments in this category yet.
              </NavioraText>
            </View>
          )}
          <View style={{ height: 100 }} />
        </ScrollView>

        <TouchableOpacity style={styles.fab} onPress={() => navigation.navigate('Voice')}>
          <LinearGradient colors={theme.colors.gradients.primary} style={styles.fabGradient}>
            <Ionicons name="add" size={32} color="#FFF" />
          </LinearGradient>
        </TouchableOpacity>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 24 },
  iconBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  tabContainer: { flexDirection: 'row', paddingHorizontal: 24, marginBottom: 20 },
  tabBtn: { flex: 1, paddingVertical: 12, alignItems: 'center' },
  scrollContent: { paddingHorizontal: 24 },
  card: { padding: 20, marginBottom: 16 },
  cardTop: { flexDirection: 'row', alignItems: 'center' },
  avatar: { width: 56, height: 56, borderRadius: 28 },
  cardMain: { flex: 1, marginLeft: 16 },
  cardDivider: { height: 1, backgroundColor: 'rgba(255,255,255,0.05)', marginVertical: 16 },
  cardBottom: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
  infoRow: { flexDirection: 'row', alignItems: 'center' },
  actionRow: { flexDirection: 'row', gap: 12 },
  actionBtn: { flex: 1, paddingVertical: 8, borderRadius: 12, borderWidth: 1, alignItems: 'center' },
  emptyState: { alignItems: 'center', marginTop: 60, paddingHorizontal: 40 },
  fab: { position: 'absolute', bottom: 100, right: 24, width: 64, height: 64, borderRadius: 32, elevation: 5, shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 10 },
  fabGradient: { flex: 1, borderRadius: 32, justifyContent: 'center', alignItems: 'center' },
});
