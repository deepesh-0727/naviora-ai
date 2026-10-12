import React, { useEffect, useState, useCallback } from 'react';
import { Alert, Modal, StyleSheet, View, ScrollView, TouchableOpacity, SafeAreaView, ActivityIndicator, RefreshControl, Image, Dimensions, TextInput } from 'react-native';
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
  const [rescheduleTarget, setRescheduleTarget] = useState<AppointmentItem | null>(null);
  const [newDateTime, setNewDateTime] = useState('');
  const [savingReschedule, setSavingReschedule] = useState(false);

  const fetchAppointments = useCallback(async () => {
    const result = await apiService.get<AppointmentItem[]>('/appointments');
    if (!result.data) {
      throw new Error(result.error || 'Unable to load appointments.');
    }
    setAppointments(Array.isArray(result.data) ? result.data : []);
  }, []);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetchAppointments()
      .catch(error => Alert.alert('Appointments unavailable', error instanceof Error ? error.message : 'Unable to load appointments.'))
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [fetchAppointments]);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await fetchAppointments();
    } catch (error) {
      Alert.alert('Refresh failed', error instanceof Error ? error.message : 'Unable to refresh appointments.');
    } finally {
      setRefreshing(false);
    }
  };

  const cancelAppointment = async (id: number) => {
    try {
      const result = await apiService.delete(`/appointments/${id}`);
      if (result.error || !result.data) {
        throw new Error(result.error || 'Unable to cancel this appointment.');
      }
      setAppointments(current => current.map(item => item.id === id ? { ...item, status: 'cancelled' } : item));
      Alert.alert('Appointment canceled', 'Your appointment has been canceled.');
    } catch (error) {
      Alert.alert('Cancellation failed', error instanceof Error ? error.message : 'Unable to cancel this appointment.');
    }
  };

  const confirmCancelAppointment = (appointment: AppointmentItem) => {
    Alert.alert(
      'Cancel appointment?',
      `Cancel your appointment with ${appointment.doctor_name}?`,
      [
        { text: 'Keep appointment', style: 'cancel' },
        { text: 'Cancel appointment', style: 'destructive', onPress: () => cancelAppointment(appointment.id) },
      ]
    );
  };

  const openReschedule = (appointment: AppointmentItem) => {
    const date = new Date(appointment.scheduled_time);
    const pad = (value: number) => String(value).padStart(2, '0');
    setNewDateTime(Number.isNaN(date.getTime())
      ? ''
      : `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`);
    setRescheduleTarget(appointment);
  };

  const saveReschedule = async () => {
    if (!rescheduleTarget) return;
    const parsedDate = new Date(newDateTime.trim().replace(' ', 'T'));
    if (Number.isNaN(parsedDate.getTime()) || parsedDate.getTime() <= Date.now()) {
      Alert.alert('Invalid date and time', 'Enter a future date and time using YYYY-MM-DD HH:mm.');
      return;
    }

    setSavingReschedule(true);
    try {
      const scheduledTime = parsedDate.toISOString();
      const result = await apiService.put<{ message: string }>(`/appointments/${rescheduleTarget.id}`, {
        scheduled_time: scheduledTime,
      });
      if (result.error || !result.data) {
        throw new Error(result.error || 'Unable to reschedule this appointment.');
      }
      setAppointments(current => current.map(item =>
        item.id === rescheduleTarget.id ? { ...item, scheduled_time: scheduledTime } : item
      ));
      setRescheduleTarget(null);
      Alert.alert('Appointment rescheduled', 'Your new appointment time has been saved.');
    } catch (error) {
      Alert.alert('Rescheduling failed', error instanceof Error ? error.message : 'Unable to reschedule this appointment.');
    } finally {
      setSavingReschedule(false);
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
          <TouchableOpacity style={[styles.actionBtn, { borderColor: theme.colors.glass.border }]} onPress={() => openReschedule(item)} disabled={item.status !== 'scheduled'}>
            <NavioraText type="xs" color="low">Reschedule</NavioraText>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.actionBtn, { borderColor: theme.colors.glass.border }]} onPress={() => confirmCancelAppointment(item)} disabled={item.status !== 'scheduled'}>
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

      <Modal visible={rescheduleTarget !== null} transparent animationType="slide" onRequestClose={() => setRescheduleTarget(null)}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalCard, { backgroundColor: theme.colors.surface }]}>
            <NavioraText type="h3">Reschedule appointment</NavioraText>
            <NavioraText type="xs" color="low" style={{ marginTop: 8 }}>
              Enter a future date and time (YYYY-MM-DD HH:mm).
            </NavioraText>
            <TextInput
              value={newDateTime}
              onChangeText={setNewDateTime}
              placeholder="2026-12-31 14:30"
              placeholderTextColor={theme.colors.text.low}
              accessibilityLabel="New appointment date and time"
              style={[styles.dateTimeInput, { color: theme.colors.text.high, borderColor: theme.colors.border }]}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <View style={styles.modalActions}>
              <TouchableOpacity onPress={() => setRescheduleTarget(null)} disabled={savingReschedule} style={styles.modalAction}>
                <NavioraText type="label" color="low">Back</NavioraText>
              </TouchableOpacity>
              <TouchableOpacity onPress={saveReschedule} disabled={savingReschedule} style={styles.modalAction}>
                {savingReschedule
                  ? <ActivityIndicator color={theme.colors.primary} />
                  : <NavioraText type="label" color="primary">Save time</NavioraText>}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
  modalOverlay: { flex: 1, justifyContent: 'center', padding: 24, backgroundColor: 'rgba(0,0,0,0.55)' },
  modalCard: { padding: 24, borderRadius: 20 },
  dateTimeInput: { borderWidth: 1, borderRadius: 12, padding: 14, marginTop: 20, fontSize: 16 },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', marginTop: 20, gap: 24 },
  modalAction: { minWidth: 64, minHeight: 44, justifyContent: 'center', alignItems: 'center' },
});
