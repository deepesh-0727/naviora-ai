import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, Text, TextInput, View } from 'react-native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';
import { useWardState } from '../hooks/useWardState';
import type { WardBed } from '../hooks/useWardState';

type Entry = Record<string, unknown>;
function itemList(value: unknown): Entry[] {
  if (Array.isArray(value)) return value.filter((item): item is Entry => typeof item === 'object' && item !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) return value.items.filter((item): item is Entry => typeof item === 'object' && item !== null);
  return [];
}
function textValue(entry: Entry, keys: string[]): string {
  for (const key of keys) {
    const value = entry[key];
    if (typeof value === 'string' || typeof value === 'number') return String(value);
  }
  return '—';
}

export default function NurseDashboard() {
  const [wardIdInput, setWardIdInput] = useState('');
  const wardId = wardIdInput.trim() ? wardIdInput.trim() : null;
  const { beds, loading: bedsLoading, error: bedsError, backendUnavailable: bedsUnavailable, empty: bedsEmpty, refresh: refreshBeds } = useWardState(wardId);
  const [medications, setMedications] = useState<Entry[]>([]);
  const [vitalsDue, setVitalsDue] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [missingEndpoint, setMissingEndpoint] = useState<string | null>(null);
  const [patientId, setPatientId] = useState('');
  const [notes, setNotes] = useState('');
  const [systolic, setSystolic] = useState('');
  const [diastolic, setDiastolic] = useState('');
  const [heartRate, setHeartRate] = useState('');
  const [temperature, setTemperature] = useState('');
  const [spo2, setSpo2] = useState('');
  const [alerts, setAlerts] = useState<string[]>([]);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const refreshTasks = useCallback(async () => {
    if (!wardId) return;
    setLoading(true);
    setError(null);
    setMissingEndpoint(null);
    try {
      const [medicationResponse, vitalsResponse] = await Promise.all([
        apiClient.get<unknown>(buildApiUrl('nurse', `/nurse/ward/${encodeURIComponent(wardId)}/medications/due`)),
        apiClient.get<unknown>(buildApiUrl('nurse', `/nurse/ward/${encodeURIComponent(wardId)}/vitals/due`)),
      ]);
      setMedications(itemList(medicationResponse.data));
      setVitalsDue(itemList(vitalsResponse.data));
    } catch (reason: unknown) {
      const details = typeof reason === 'object' && reason !== null && 'response' in reason ? reason as { response?: { status?: number }; config?: { url?: string } } : {};
      if (details.response?.status === 404 || details.response?.status === 501) setMissingEndpoint(details.config?.url ?? 'GET /staff/nurse/ward/{id}/medications/due');
      else setError('Could not load ward tasks.');
    } finally { setLoading(false); }
  }, [wardId]);

  useEffect(() => {
    const events = ['vital_critical', 'call_bell', 'fall_detected'];
    void websocketClient.connect();
    const unsubscribers = events.map((eventName) => websocketClient.subscribe(eventName, (payload) => {
      const detail = typeof payload === 'object' && payload !== null && 'message' in payload && typeof payload.message === 'string' ? payload.message : eventName.replace(/_/g, ' ');
      setAlerts((current) => [detail, ...current].slice(0, 8));
    }));
    return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
  }, []);

  const sendAction = async (kind: 'vitals' | 'medication' | 'handover') => {
    if ((kind !== 'handover' && !patientId.trim()) || !notes.trim()) { setError('Enter the required patient identifier and details before submitting.'); return; }
    if (kind === 'vitals' && [systolic, diastolic, heartRate, temperature, spo2].some((value) => !Number.isFinite(Number(value)) || Number(value) <= 0)) {
      setError('Enter valid blood pressure, heart rate, temperature, and oxygen saturation values.');
      return;
    }
    setLoading(true); setError(null); setMissingEndpoint(null); setActionMessage(null);
    const endpoint = kind === 'vitals' ? '/nurse/vitals' : kind === 'medication' ? '/nurse/medications/record' : '/nurse/handover';
    const payload: Record<string, unknown> = kind === 'vitals'
      ? { patient_id: Number(patientId), blood_pressure_systolic: Number(systolic), blood_pressure_diastolic: Number(diastolic), heart_rate: Number(heartRate), temperature: Number(temperature), spo2: Number(spo2), notes: notes.trim() }
      : { patient_id: patientId.trim() ? Number(patientId) : undefined, details: notes.trim(), ward_id: wardId ?? undefined };
    try {
      await apiClient.post(buildApiUrl('nurse', endpoint), payload);
      setActionMessage(`${kind === 'vitals' ? 'Vitals' : kind === 'medication' ? 'Medication' : 'Handover'} record submitted.`);
      setNotes('');
      if (kind === 'vitals') await refreshTasks();
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number }; config?: { url?: string } }).response?.status : undefined;
      if (status === 404 || status === 501) setMissingEndpoint(`POST /staff${endpoint}`);
      else setError('Could not submit the nursing record. Retry when ready.');
    } finally { setLoading(false); }
  };

  const bedColor = (status: string) => status.toLowerCase() === 'occupied' ? '#FADBD8' : status.toLowerCase() === 'critical' ? '#F5B7B1' : status.toLowerCase() === 'cleaning' ? '#FCF3CF' : '#D5F5E3';

  return (
    <ScreenContainer>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
        <SectionHeader title="Nurse Dashboard" />
        {(error || bedsError) ? <ErrorState message={error ?? bedsError ?? 'Could not load ward state.'} onRetry={() => { void refreshTasks(); void refreshBeds(); }} /> : null}
        {missingEndpoint || bedsUnavailable ? <BackendNotAvailable endpoint={missingEndpoint ?? 'GET /staff/nurse/ward/{id}/beds'} /> : null}
        {actionMessage ? <Text style={{ color: '#1D8A6C', marginBottom: 10 }}>{actionMessage}</Text> : null}
        <Card style={{ marginBottom: 12 }}>
          <Text style={{ fontWeight: '700', marginBottom: 8 }}>Ward</Text>
          <TextInput value={wardIdInput} onChangeText={setWardIdInput} placeholder="Enter assigned ward ID" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <Button title="Load ward tasks" onPress={() => { void refreshBeds(); void refreshTasks(); }} />
        </Card>
        <Card style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Bed status</Text>
          {bedsLoading ? <Loader message="Loading beds…" /> : bedsEmpty ? <EmptyState message={wardId ? 'No beds are assigned to this ward.' : 'Enter a ward ID to load live bed status.'} /> : (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{beds.map((bed: WardBed, index) => {
              const status = textValue(bed, ['status']);
              return <View key={textValue(bed, ['id', 'bed_id']) + index} style={{ minWidth: 95, padding: 10, borderRadius: 10, backgroundColor: bedColor(status) }}><Text style={{ fontWeight: '700' }}>{textValue(bed, ['bed_number', 'name', 'id'])}</Text><Text>{status}</Text></View>;
            })}</View>
          )}
        </Card>
        {loading ? <Loader message="Loading nursing tasks…" /> : null}
        <Card style={{ marginBottom: 12 }}><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Medication timeline</Text>{medications.length ? medications.map((item, index) => <Text key={textValue(item, ['id']) + index} style={{ paddingVertical: 5 }}>{textValue(item, ['due_at', 'scheduled_time'])} · Patient {textValue(item, ['patient_id'])} · {textValue(item, ['medication', 'name'])}</Text>) : <EmptyState message="No medication doses are due." />}</Card>
        <Card style={{ marginBottom: 12 }}><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Vitals due</Text>{vitalsDue.length ? vitalsDue.map((item, index) => <Text key={textValue(item, ['patient_id']) + index} style={{ paddingVertical: 5 }}>Patient {textValue(item, ['patient_id'])} · {textValue(item, ['due_at', 'reason'])}</Text>) : <EmptyState message="No vitals are currently due." />}</Card>
        <Card style={{ marginBottom: 12 }}><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Live alerts</Text>{alerts.length ? alerts.map((alert, index) => <Text key={`${alert}-${index}`} style={{ color: '#B42318', paddingVertical: 4 }}>{alert}</Text>) : <EmptyState message="No active ward alerts." />}</Card>
        <Card><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Record care / handover</Text>
          <TextInput value={patientId} onChangeText={setPatientId} placeholder="Patient ID (leave blank for handover)" keyboardType="number-pad" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <TextInput value={systolic} onChangeText={setSystolic} keyboardType="number-pad" placeholder="Systolic" style={{ flex: 1, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
            <TextInput value={diastolic} onChangeText={setDiastolic} keyboardType="number-pad" placeholder="Diastolic" style={{ flex: 1, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          </View>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <TextInput value={heartRate} onChangeText={setHeartRate} keyboardType="number-pad" placeholder="Heart rate" style={{ flex: 1, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
            <TextInput value={temperature} onChangeText={setTemperature} keyboardType="decimal-pad" placeholder="Temp °C" style={{ flex: 1, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
            <TextInput value={spo2} onChangeText={setSpo2} keyboardType="number-pad" placeholder="SpO₂" style={{ flex: 1, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          </View>
          <TextInput value={notes} onChangeText={setNotes} placeholder="Vitals, medication, or handover details" multiline style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, minHeight: 72, marginBottom: 8 }} />
          <View style={{ gap: 8 }}><Button title="Record vitals" disabled={loading} onPress={() => void sendAction('vitals')} /><Button title="Record medication" variant="secondary" disabled={loading} onPress={() => void sendAction('medication')} /><Button title="Submit handover" variant="secondary" disabled={loading} onPress={() => void sendAction('handover')} /></View>
        </Card>
      </ScrollView>
    </ScreenContainer>
  );
}
