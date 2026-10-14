import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, Text, TextInput, View } from 'react-native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';

type Entry = Record<string, unknown>;
function list(value: unknown): Entry[] {
  if (Array.isArray(value)) return value.filter((item): item is Entry => typeof item === 'object' && item !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) return value.items.filter((item): item is Entry => typeof item === 'object' && item !== null);
  return [];
}
function field(entry: Entry, keys: string[]): string {
  for (const key of keys) { const value = entry[key]; if (typeof value === 'string' || typeof value === 'number') return String(value); }
  return '—';
}

export default function FacilitiesDashboard() {
  const [ward, setWard] = useState('');
  const [beds, setBeds] = useState<Entry[]>([]);
  const [orSchedule, setOrSchedule] = useState<Entry[]>([]);
  const [equipment, setEquipment] = useState<Entry[]>([]);
  const [roster, setRoster] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [maintenanceText, setMaintenanceText] = useState('');
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true); setError(null); setUnavailable(null);
    try {
      const wardPath = ward.trim() ? `/facilities/wards/${encodeURIComponent(ward.trim())}/beds` : '/facilities/beds';
      const [bedResponse, orResponse, equipmentResponse, rosterResponse] = await Promise.all([
        apiClient.get<unknown>(buildApiUrl('facilities', wardPath)),
        apiClient.get<unknown>(buildApiUrl('facilities', '/facilities/or-schedule')),
        apiClient.get<unknown>(buildApiUrl('facilities', '/facilities/equipment')),
        apiClient.get<unknown>(buildApiUrl('facilities', '/facilities/roster')),
      ]);
      setBeds(list(bedResponse.data)); setOrSchedule(list(orResponse.data)); setEquipment(list(equipmentResponse.data)); setRoster(list(rosterResponse.data));
    } catch (reason: unknown) {
      const detail = typeof reason === 'object' && reason !== null && 'response' in reason ? reason as { response?: { status?: number }; config?: { url?: string } } : {};
      if (detail.response?.status === 404 || detail.response?.status === 501) setUnavailable(detail.config?.url ?? 'GET /staff/facilities/beds');
      else setError('Could not load facilities information.');
    } finally { setLoading(false); }
  }, [ward]);
  useEffect(() => { void refresh(); }, [refresh]);

  const updateBed = async (bed: Entry) => {
    const id = field(bed, ['id', 'bed_id']);
    if (id === '—') { setActionError('This bed entry has no identifier.'); return; }
    setBusy(true); setActionError(null); setActionMessage(null);
    try {
      const status = field(bed, ['status']).toLowerCase() === 'available' ? 'cleaning' : 'available';
      await apiClient.put(buildApiUrl('facilities', `/facilities/beds/${encodeURIComponent(id)}/status`), { status });
      setActionMessage(`Bed ${id} status updated.`); await refresh();
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      setActionError(status === 404 || status === 501 ? 'Bed status updates are not available on the backend yet.' : 'Could not update bed status.');
    } finally { setBusy(false); }
  };

  const requestMaintenance = async () => {
    if (!maintenanceText.trim()) { setActionError('Describe the maintenance issue first.'); return; }
    setBusy(true); setActionError(null); setActionMessage(null);
    try {
      await apiClient.post(buildApiUrl('facilities', '/facilities/maintenance'), { description: maintenanceText.trim(), ward_id: ward.trim() || undefined });
      setMaintenanceText(''); setActionMessage('Maintenance request submitted.');
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      setActionError(status === 404 || status === 501 ? 'Maintenance requests are not available on the backend yet.' : 'Could not submit the maintenance request.');
    } finally { setBusy(false); }
  };

  if (loading) return <Loader message="Loading facilities…" />;
  if (unavailable) return <ScreenContainer><BackendNotAvailable endpoint={unavailable} /><Button title="Retry" variant="secondary" onPress={() => void refresh()} /></ScreenContainer>;
  if (error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  return (
    <ScreenContainer>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
        <SectionHeader title="Facilities" />
        {actionError ? <Text style={{ color: '#B42318', marginBottom: 8 }}>{actionError}</Text> : null}
        {actionMessage ? <Text style={{ color: '#1D8A6C', marginBottom: 8 }}>{actionMessage}</Text> : null}
        <Card style={{ marginBottom: 12 }}><TextInput value={ward} onChangeText={setWard} placeholder="Filter by ward ID (optional)" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} /><Button title="Refresh facilities" variant="secondary" onPress={() => void refresh()} /></Card>
        <Card style={{ marginBottom: 12 }}><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Beds</Text>{beds.length ? <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{beds.map((bed, index) => <View key={field(bed, ['id', 'bed_id']) + index} style={{ minWidth: 110, padding: 10, borderRadius: 10, backgroundColor: '#EAF9F3' }}><Text style={{ fontWeight: '700' }}>{field(bed, ['bed_number', 'name', 'id'])}</Text><Text>{field(bed, ['status'])}</Text><Button title="Change status" variant="secondary" disabled={busy} onPress={() => void updateBed(bed)} /></View>)}</View> : <EmptyState message="No bed records are available." />}</Card>
        <Card style={{ marginBottom: 12 }}><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Operating room schedule</Text>{orSchedule.length ? orSchedule.map((item, index) => <Text key={field(item, ['id']) + index} style={{ paddingVertical: 5 }}>{field(item, ['scheduled_time', 'date'])} · {field(item, ['room', 'room_name'])} · {field(item, ['procedure', 'status'])}</Text>) : <EmptyState message="No operating room bookings are listed." />}</Card>
        <Card style={{ marginBottom: 12 }}><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Equipment</Text>{equipment.length ? equipment.map((item, index) => <Text key={field(item, ['id']) + index} style={{ paddingVertical: 5 }}>{field(item, ['name', 'type'])} · {field(item, ['status', 'condition'])} · {field(item, ['location'])}</Text>) : <EmptyState message="No equipment records are available." />}</Card>
        <Card style={{ marginBottom: 12 }}><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Roster</Text>{roster.length ? roster.map((item, index) => <Text key={field(item, ['id', 'staff_id']) + index} style={{ paddingVertical: 5 }}>{field(item, ['name', 'staff_name'])} · {field(item, ['role'])} · {field(item, ['shift', 'shift_start'])}</Text>) : <EmptyState message="No facilities roster entries are available." />}</Card>
        <Card><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Maintenance request</Text><TextInput value={maintenanceText} onChangeText={setMaintenanceText} placeholder="Describe equipment or facility issue" multiline style={{ minHeight: 72, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} /><Button title={busy ? 'Submitting…' : 'Submit request'} disabled={busy} onPress={() => void requestMaintenance()} /></Card>
      </ScrollView>
    </ScreenContainer>
  );
}
