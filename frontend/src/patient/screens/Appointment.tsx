import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Modal,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAppointments } from '../hooks/useAppointments';
import { colors } from '../../shared/theme/colors';
import { websocketClient } from '../../shared/services/websocket';
import type { Appointment, Department, Doctor } from '../../shared/services/api';
import {
  BackendNotAvailable,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  Loader,
  SectionHeader,
  Badge,
} from '../../shared/components';

type TabKey = 'upcoming' | 'past';

function statusColor(status: string): string {
  if (status === 'confirmed') return colors.primary;
  if (status === 'pending') return colors.accent;
  if (status === 'cancelled') return colors.danger;
  return colors.textMuted;
}

// ─── Book Wizard ─────────────────────────────────────────────────────────────

interface BookWizardProps {
  visible: boolean;
  onClose: () => void;
  departments: Department[];
  doctors: Doctor[];
  availability: string[];
  onSelectDept: (id: number) => void;
  onSelectDoctor: (id: number) => void;
  onBook: (payload: { doctor_id: number; department_id: number; scheduled_time: string; symptoms?: string }) => Promise<void>;
}

function BookWizard({ visible, onClose, departments, doctors, availability, onSelectDept, onSelectDoctor, onBook }: BookWizardProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedDept, setSelectedDept] = useState<Department | null>(null);
  const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [symptoms, setSymptoms] = useState('');
  const [booking, setBooking] = useState(false);

  const reset = () => {
    setStep(1);
    setSelectedDept(null);
    setSelectedDoctor(null);
    setSelectedSlot(null);
    setSymptoms('');
    setBooking(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleBook = async () => {
    if (!selectedDoctor || !selectedDept || !selectedSlot) return;
    setBooking(true);
    await onBook({
      doctor_id: selectedDoctor.id,
      department_id: selectedDept.id,
      scheduled_time: selectedSlot,
      symptoms: symptoms || undefined,
    });
    setBooking(false);
    handleClose();
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={handleClose}>
      <View style={styles.overlay}>
        <View style={styles.wizardSheet}>
          <View style={styles.wizardHeader}>
            <Text style={styles.wizardTitle}>
              {step === 1 ? 'Select Department' : step === 2 ? 'Select Doctor' : 'Pick a Slot'}
            </Text>
            <TouchableOpacity onPress={handleClose} accessibilityLabel="Close booking"><Text style={{ fontSize: 20 }}>✕</Text></TouchableOpacity>
          </View>

          {step === 1 && (
            <ScrollView>
              {departments.length === 0
                ? <EmptyState message="No departments available" />
                : departments.map((d) => (
                  <TouchableOpacity
                    key={d.id}
                    style={[styles.listItem, selectedDept?.id === d.id && styles.listItemActive]}
                    onPress={() => { setSelectedDept(d); onSelectDept(d.id); setStep(2); }}
                  >
                    <Text style={styles.listItemText}>{d.name}</Text>
                  </TouchableOpacity>
                ))}
            </ScrollView>
          )}

          {step === 2 && (
            <ScrollView>
              {doctors.length === 0
                ? <EmptyState message="No doctors found for this department" />
                : doctors.map((doc) => {
                  const name = doc.name ?? `${doc.first_name ?? ''} ${doc.last_name ?? ''}`.trim();
                  return (
                    <TouchableOpacity
                      key={doc.id}
                      style={[styles.listItem, selectedDoctor?.id === doc.id && styles.listItemActive]}
                      onPress={() => { setSelectedDoctor(doc); onSelectDoctor(doc.id); setStep(3); }}
                    >
                      <Text style={styles.listItemText}>{name}</Text>
                      {doc.specialization ? <Text style={styles.listItemSub}>{doc.specialization}</Text> : null}
                    </TouchableOpacity>
                  );
                })}
            </ScrollView>
          )}

          {step === 3 && (
            <ScrollView>
              <Input label="Symptoms (optional)" value={symptoms} onChangeText={setSymptoms} placeholder="Describe your symptoms" />
              <Text style={styles.slotLabel}>Available slots</Text>
              {availability.length === 0
                ? <EmptyState message="No available slots" />
                : (
                  <View style={styles.slotGrid}>
                    {availability.map((slot) => (
                      <TouchableOpacity
                        key={slot}
                        style={[styles.slot, selectedSlot === slot && styles.slotActive]}
                        onPress={() => setSelectedSlot(slot)}
                        accessibilityLabel={`Slot ${slot}`}
                      >
                        <Text style={[styles.slotText, selectedSlot === slot && styles.slotTextActive]}>
                          {new Date(slot).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                )}
              <Button
                title={booking ? 'Booking…' : 'Confirm Booking'}
                onPress={() => { void handleBook(); }}
                disabled={!selectedSlot || booking}
                style={{ marginTop: 16 }}
              />
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
}

// ─── Appointment Card ─────────────────────────────────────────────────────────

function ApptCard({
  item,
  onCancel,
  onReschedule,
}: {
  item: Appointment;
  onCancel: (id: number) => void;
  onReschedule: (id: number) => void;
}) {
  return (
    <Card style={styles.apptCard}>
      <View style={styles.apptRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.apptDoctor}>{item.doctor_name}</Text>
          <Text style={styles.apptDept}>{item.department_name}</Text>
          <Text style={styles.apptTime}>{new Date(item.scheduled_time).toLocaleString()}</Text>
        </View>
        <Badge label={item.status} color={statusColor(item.status)} />
      </View>
      {item.status !== 'cancelled' && (
        <View style={styles.apptActions}>
          <Button title="Reschedule" variant="secondary" onPress={() => onReschedule(item.id)} style={styles.actionBtn} />
          <Button title="Cancel" variant="danger" onPress={() => onCancel(item.id)} style={styles.actionBtn} />
        </View>
      )}
    </Card>
  );
}

// ─── Main Screen ──────────────────────────────────────────────────────────────

export default function AppointmentScreen() {
  const {
    upcoming,
    past,
    departments,
    doctors,
    availability,
    loading,
    error,
    backendUnavailable,
    refresh,
    fetchDoctors,
    fetchAvailability,
    book,
    cancel,
    reschedule,
  } = useAppointments();

  const [tab, setTab] = useState<TabKey>('upcoming');
  const [showWizard, setShowWizard] = useState(false);

  const handleCancel = useCallback(async (id: number) => {
    Alert.alert('Cancel Appointment', 'Are you sure?', [
      { text: 'No', style: 'cancel' },
      {
        text: 'Yes, Cancel',
        style: 'destructive',
        onPress: async () => {
          const ok = await cancel(id);
          if (!ok) Alert.alert('Error', 'Failed to cancel appointment.');
        },
      },
    ]);
  }, [cancel]);

  const handleReschedule = useCallback((id: number) => {
    Alert.alert('Reschedule', `Reschedule appointment #${id}? (Select a new slot)`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Choose slot',
        onPress: () => {
          // For now, open the wizard context-free — a future iteration will pass the appointment ID
          setShowWizard(true);
        },
      },
    ]);
  }, []);

  useEffect(() => {
    void websocketClient.connect();
    const unsub = websocketClient.subscribe('appointment_update', () => {
      refresh();
    });
    return () => {
      unsub();
    };
  }, [refresh]);

  if (backendUnavailable) {
    return (
      <SafeAreaView style={styles.safe}>
        <BackendNotAvailable endpoint="GET /appointments" />
      </SafeAreaView>
    );
  }

  const list = tab === 'upcoming' ? upcoming : past;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.screenHeading}><SectionHeader title="Appointments" /><Text style={styles.screenSubtitle}>Your visits, schedule and booking options</Text></View>
      {/* Tab bar */}
      <View style={styles.tabRow}>
        {(['upcoming', 'past'] as TabKey[]).map((t) => (
          <TouchableOpacity
            key={t}
            style={[styles.tabBtn, tab === t && styles.tabBtnActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[styles.tabBtnText, tab === t && styles.tabBtnTextActive]}>
              {t === 'upcoming' ? 'Upcoming' : 'Past'}
            </Text>
          </TouchableOpacity>
        ))}
        <TouchableOpacity
          style={styles.bookBtn}
          onPress={() => setShowWizard(true)}
          accessibilityLabel="Book appointment"
        >
          <Text style={styles.bookBtnText}>+ Book</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <Loader message="Loading appointments…" />
      ) : error ? (
        <ErrorState message={error} onRetry={refresh} />
      ) : (
        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} />}
        >
          {list.length === 0
            ? <EmptyState message={tab === 'upcoming' ? 'No upcoming appointments' : 'No past appointments'} />
            : list.map((a) => (
              <ApptCard
                key={a.id}
                item={a}
                onCancel={(id) => { void handleCancel(id); }}
                onReschedule={handleReschedule}
              />
            ))}
        </ScrollView>
      )}

      <BookWizard
        visible={showWizard}
        onClose={() => setShowWizard(false)}
        departments={departments}
        doctors={doctors}
        availability={availability}
        onSelectDept={(id) => { void fetchDoctors(id); }}
        onSelectDoctor={(id) => { void fetchAvailability(id); }}
        onBook={async (payload) => {
          const result = await book(payload);
          if (!result) Alert.alert('Error', 'Booking failed. Please try again.');
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  screenHeading: { paddingHorizontal: 16, paddingTop: 8 },
  screenSubtitle: { color: colors.textMuted, marginBottom: 8, marginTop: -8 },
  tabRow: { flexDirection: 'row', alignItems: 'center', padding: 16, gap: 8 },
  tabBtn: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 999, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border },
  tabBtnActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  tabBtnText: { fontSize: 13, color: colors.textMuted, fontWeight: '600' },
  tabBtnTextActive: { color: colors.white },
  bookBtn: { marginLeft: 'auto', backgroundColor: colors.primary, paddingHorizontal: 16, paddingVertical: 9, borderRadius: 999 },
  bookBtnText: { color: colors.white, fontWeight: '700', fontSize: 13 },
  scroll: { paddingHorizontal: 16, paddingBottom: 100 },
  apptCard: { marginBottom: 10 },
  apptRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  apptDoctor: { fontSize: 15, fontWeight: '700', color: colors.text },
  apptDept: { fontSize: 13, color: colors.textMuted },
  apptTime: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  apptActions: { flexDirection: 'row', gap: 8, marginTop: 10, justifyContent: 'flex-end' },
  actionBtn: { flex: 1 },
  // Wizard
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  wizardSheet: { backgroundColor: colors.white, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, maxHeight: '80%' },
  wizardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  wizardTitle: { fontSize: 18, fontWeight: '700', color: colors.text },
  listItem: { padding: 14, borderRadius: 12, marginBottom: 8, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border },
  listItemActive: { backgroundColor: colors.primaryLight, borderColor: colors.primary },
  listItemText: { fontSize: 15, color: colors.text, fontWeight: '600' },
  listItemSub: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  slotLabel: { fontSize: 14, fontWeight: '700', color: colors.text, marginBottom: 10, marginTop: 8 },
  slotGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  slot: { paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border },
  slotActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  slotText: { fontSize: 13, color: colors.text, fontWeight: '600' },
  slotTextActive: { color: colors.white },
});
