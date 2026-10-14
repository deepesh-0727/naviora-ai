import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, Text, TextInput, View } from 'react-native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';

type Entry = Record<string, unknown>;
function asEntries(value: unknown): Entry[] {
  if (Array.isArray(value)) return value.filter((item): item is Entry => typeof item === 'object' && item !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) return value.items.filter((item): item is Entry => typeof item === 'object' && item !== null);
  return [];
}
function valueOf(entry: Entry, keys: string[]): string {
  for (const key of keys) { const value = entry[key]; if (typeof value === 'string' || typeof value === 'number') return String(value); }
  return '—';
}

export default function FrontDeskDashboard() {
  const [doctorLoad, setDoctorLoad] = useState<Entry[]>([]);
  const [doctorsLoading, setDoctorsLoading] = useState(true);
  const [doctorsError, setDoctorsError] = useState<string | null>(null);
  const [doctorsUnavailable, setDoctorsUnavailable] = useState(false);
  const [patientSearch, setPatientSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Entry[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchUnavailable, setSearchUnavailable] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [patientId, setPatientId] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [amount, setAmount] = useState('');
  const [loadingAction, setLoadingAction] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionUnavailable, setActionUnavailable] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [availability, setAvailability] = useState<Entry[]>([]);

  const loadDoctors = useCallback(async () => {
    setDoctorsLoading(true); setDoctorsError(null); setDoctorsUnavailable(false);
    try {
      const response = await apiClient.get<unknown>(buildApiUrl('front_desk', '/doctors/load'));
      setDoctorLoad(asEntries(response.data));
    } catch (reason: unknown) {
      const detail = typeof reason === 'object' && reason !== null && 'response' in reason ? reason as { response?: { status?: number } } : {};
      if (detail.response?.status === 404 || detail.response?.status === 501) setDoctorsUnavailable(true);
      else setDoctorsError('Could not load doctor availability.');
    } finally { setDoctorsLoading(false); }
  }, []);
  useEffect(() => { void loadDoctors(); }, [loadDoctors]);

  const searchPatients = async () => {
    if (!patientSearch.trim()) { setSearchError('Enter a name, phone, or patient ID.'); return; }
    setSearching(true); setSearchError(null); setSearchUnavailable(false);
    try {
      const response = await apiClient.get<unknown>(buildApiUrl('front_desk', '/patients/search'), { params: { q: patientSearch.trim() } });
      setSearchResults(asEntries(response.data));
    } catch (reason: unknown) {
      const detail = typeof reason === 'object' && reason !== null && 'response' in reason ? reason as { response?: { status?: number } } : {};
      if (detail.response?.status === 404 || detail.response?.status === 501) setSearchUnavailable(true);
      else setSearchError('Patient search failed. Retry the search.');
    } finally { setSearching(false); }
  };

  const requestAvailability = async () => {
    if (!doctorId.trim()) { setActionError('Enter a doctor ID to check availability.'); return; }
    setLoadingAction(true); setActionError(null); setActionUnavailable(null);
    try {
      const response = await apiClient.get<unknown>(buildApiUrl('front_desk', '/availability'), { params: { doctor_id: doctorId.trim(), date: scheduledTime.trim().slice(0, 10) } });
      setAvailability(asEntries(response.data));
      if (typeof response.data === 'object' && response.data !== null && 'available_slots' in response.data && Array.isArray(response.data.available_slots)) {
        setAvailability(response.data.available_slots.map((slot, index) => ({ id: index, slot })));
      }
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      if (status === 404 || status === 501) setActionUnavailable('GET /staff/availability'); else setActionError('Could not retrieve appointment availability.');
    } finally { setLoadingAction(false); }
  };

  const submit = async (kind: 'walk-in' | 'appointment' | 'payment') => {
    setLoadingAction(true); setActionError(null); setActionUnavailable(null); setMessage(null);
    let path: string;
    let payload: Entry;
    if (kind === 'walk-in') {
      if (!name.trim() || !phone.trim()) { setActionError('Patient name and phone are required.'); setLoadingAction(false); return; }
      path = '/patients/walk-in'; payload = { full_name: name.trim(), email: email.trim() || undefined, phone: phone.trim() };
    } else if (kind === 'appointment') {
      if (!patientId.trim() || !doctorId.trim() || !scheduledTime.trim()) { setActionError('Patient ID, doctor ID, and appointment date/time are required.'); setLoadingAction(false); return; }
      path = '/appointments'; payload = { patient_id: Number(patientId), doctor_id: Number(doctorId), scheduled_time: scheduledTime.trim() };
    } else {
      if (!patientId.trim() || !amount.trim() || !Number.isFinite(Number(amount))) { setActionError('Patient ID and a valid payment amount are required.'); setLoadingAction(false); return; }
      path = '/payments'; payload = { patient_id: Number(patientId), amount: Number(amount) };
    }
    try {
      await apiClient.post(buildApiUrl('front_desk', path), payload);
      setMessage(kind === 'walk-in' ? 'Walk-in patient registered.' : kind === 'appointment' ? 'Appointment booked.' : 'Payment recorded.');
      if (kind === 'walk-in') { setName(''); setEmail(''); setPhone(''); }
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      if (status === 404 || status === 501) setActionUnavailable(`POST /staff${path}`); else setActionError('The request could not be completed. Check the details and retry.');
    } finally { setLoadingAction(false); }
  };

  return (
    <ScreenContainer>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
        <SectionHeader title="Front Desk" />
        {actionError ? <ErrorState message={actionError} onRetry={() => setActionError(null)} /> : null}
        {actionUnavailable ? <BackendNotAvailable endpoint={actionUnavailable} /> : null}
        {message ? <Text style={{ color: '#1D8A6C', marginBottom: 10 }}>{message}</Text> : null}
        <Card style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Patient search</Text>
          <TextInput value={patientSearch} onChangeText={setPatientSearch} placeholder="Name, phone, or patient ID" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <Button title={searching ? 'Searching…' : 'Search patients'} disabled={searching} onPress={() => void searchPatients()} />
          {searchError ? <Text style={{ color: '#B42318', marginTop: 8 }}>{searchError}</Text> : null}
          {searchUnavailable ? <BackendNotAvailable endpoint="GET /staff/patients/search" /> : searchResults.length ? searchResults.map((patient, index) => <Text key={valueOf(patient, ['id']) + index} onPress={() => setPatientId(valueOf(patient, ['id']))} style={{ paddingVertical: 8 }}>Patient {valueOf(patient, ['id'])} · {valueOf(patient, ['full_name', 'name'])} · {valueOf(patient, ['phone'])}</Text>) : <EmptyState message="Search to find registered patients." />}
        </Card>
        <Card style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Walk-in registration</Text>
          <TextInput value={name} onChangeText={setName} placeholder="Patient full name" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <TextInput value={phone} onChangeText={setPhone} placeholder="Phone number" keyboardType="phone-pad" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <TextInput value={email} onChangeText={setEmail} placeholder="Email (optional)" keyboardType="email-address" autoCapitalize="none" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <Button title={loadingAction ? 'Submitting…' : 'Register walk-in'} disabled={loadingAction} onPress={() => void submit('walk-in')} />
        </Card>
        <Card style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Booking</Text>
          <TextInput value={patientId} onChangeText={setPatientId} placeholder="Patient ID" keyboardType="number-pad" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <TextInput value={doctorId} onChangeText={setDoctorId} placeholder="Doctor ID" keyboardType="number-pad" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <TextInput value={scheduledTime} onChangeText={setScheduledTime} placeholder="Appointment date/time (ISO 8601)" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <View style={{ gap: 8 }}><Button title="Check availability" variant="secondary" disabled={loadingAction} onPress={() => void requestAvailability()} /><Button title={loadingAction ? 'Booking…' : 'Book appointment'} disabled={loadingAction} onPress={() => void submit('appointment')} /></View>
          {availability.length ? <Text style={{ marginTop: 8 }}>Available: {availability.map((slot) => valueOf(slot, ['slot', 'time'])).join(', ')}</Text> : null}
        </Card>
        <Card style={{ marginBottom: 12 }}><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Doctor load</Text>{doctorsLoading ? <Loader message="Loading doctors…" /> : doctorsError ? <ErrorState message={doctorsError} onRetry={() => void loadDoctors()} /> : doctorsUnavailable ? <BackendNotAvailable endpoint="GET /staff/doctors/load" /> : doctorLoad.length ? doctorLoad.map((doctor, index) => <Text key={valueOf(doctor, ['doctor_id', 'id']) + index} style={{ paddingVertical: 5 }}>{valueOf(doctor, ['doctor_name', 'name'])} · Load: {valueOf(doctor, ['load', 'queue_count', 'active_patients'])}</Text>) : <EmptyState message="No doctor load data available." />}</Card>
        <Card><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Record payment</Text>
          <TextInput value={amount} onChangeText={setAmount} placeholder="Amount" keyboardType="decimal-pad" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <Button title="Record payment" variant="secondary" disabled={loadingAction} onPress={() => void submit('payment')} />
        </Card>
      </ScrollView>
    </ScreenContainer>
  );
}
