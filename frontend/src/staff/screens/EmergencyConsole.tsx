import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, Text, TextInput, View } from 'react-native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, Modal, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';

type Incident = Record<string, unknown>;
function items(value: unknown): Incident[] {
  if (Array.isArray(value)) return value.filter((entry): entry is Incident => typeof entry === 'object' && entry !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) return value.items.filter((entry): entry is Incident => typeof entry === 'object' && entry !== null);
  return [];
}
function field(entry: Incident | null, keys: string[]): string {
  if (!entry) return '—';
  for (const key of keys) { const value = entry[key]; if (typeof value === 'string' || typeof value === 'number') return String(value); }
  return '—';
}

export default function EmergencyConsole() {
  const [active, setActive] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [details, setDetails] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [responderId, setResponderId] = useState('');
  const [message, setMessage] = useState('');
  const [assignVisible, setAssignVisible] = useState(false);
  const [busy, setBusy] = useState(false);

  const refreshActive = useCallback(async () => {
    setLoading(true); setError(null); setUnavailable(null);
    try {
      const response = await apiClient.get<unknown>(buildApiUrl('emergency', '/emergency/active'));
      const next = items(response.data);
      setActive(next);
      if (selectedId && !next.some((incident) => field(incident, ['id', 'emergency_id']) === selectedId)) {
        setSelectedId(null); setDetails(null);
      }
    } catch (reason: unknown) {
      const data = typeof reason === 'object' && reason !== null && 'response' in reason ? reason as { response?: { status?: number }; config?: { url?: string } } : {};
      if (data.response?.status === 404 || data.response?.status === 501) setUnavailable(data.config?.url ?? 'GET /staff/emergency/active');
      else setError('Could not load active emergency incidents.');
    } finally { setLoading(false); }
  }, [selectedId]);

  const loadDetails = useCallback(async (id: string) => {
    setSelectedId(id); setDetails(null); setDetailError(null); setDetailLoading(true);
    try {
      const response = await apiClient.get<unknown>(buildApiUrl('emergency', `/emergency/${encodeURIComponent(id)}`));
      setDetails(typeof response.data === 'object' && response.data !== null ? response.data as Incident : null);
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      setDetailError(status === 404 || status === 501 ? 'Incident detail is not available on the backend yet.' : 'Could not load incident details.');
    } finally { setDetailLoading(false); }
  }, []);

  useEffect(() => {
    void refreshActive();
    void websocketClient.connect();
    const events = ['emergency_ack', 'emergency_status', 'emergency_message'];
    const unsubscribers = events.map((name) => websocketClient.subscribe(name, () => {
      void refreshActive();
      if (selectedId) void loadDetails(selectedId);
    }));
    return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
  }, [loadDetails, refreshActive, selectedId]);

  const performAction = async (kind: 'assign' | 'message' | 'status', status?: string) => {
    if (!selectedId) { setActionError('Select an active incident first.'); return; }
    if (kind === 'assign' && !responderId.trim()) { setActionError('Enter the responder identifier.'); return; }
    if (kind === 'message' && !message.trim()) { setActionError('Enter a message to send.'); return; }
    setBusy(true); setActionError(null); setActionMessage(null);
    const path = kind === 'assign' ? `/emergency/${encodeURIComponent(selectedId)}/assign`
      : kind === 'message' ? `/emergency/${encodeURIComponent(selectedId)}/message`
        : `/emergency/${encodeURIComponent(selectedId)}/status`;
    try {
      if (kind === 'status') await apiClient.put(buildApiUrl('emergency', path), { status });
      else await apiClient.post(buildApiUrl('emergency', path), kind === 'assign' ? { responder_id: responderId.trim() } : { message: message.trim() });
      setActionMessage(kind === 'assign' ? 'Responder assigned.' : kind === 'message' ? 'Message sent.' : `Incident marked ${status}.`);
      if (kind === 'assign') setAssignVisible(false);
      if (kind === 'message') setMessage('');
      await Promise.all([refreshActive(), loadDetails(selectedId)]);
    } catch (reason: unknown) {
      const code = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      setActionError(code === 404 || code === 501 ? `${kind} action is not available on the backend yet.` : 'Emergency action failed. Retry when ready.');
    } finally { setBusy(false); }
  };

  if (loading) return <Loader message="Loading emergency feed…" />;
  if (unavailable) return <ScreenContainer><BackendNotAvailable endpoint={unavailable} /><Button title="Retry" variant="secondary" onPress={() => void refreshActive()} /></ScreenContainer>;
  if (error) return <ErrorState message={error} onRetry={() => void refreshActive()} />;

  return (
    <ScreenContainer>
      <SectionHeader title="Emergency Console" />
      {actionError ? <Text accessibilityRole="alert" style={{ color: '#B42318', marginBottom: 8 }}>{actionError}</Text> : null}
      {actionMessage ? <Text style={{ color: '#1D8A6C', marginBottom: 8 }}>{actionMessage}</Text> : null}
      <View style={{ flex: 1, flexDirection: 'row', gap: 12 }}>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingBottom: 16 }}>
          <Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Active SOS feed</Text>
          {active.length === 0 ? <EmptyState message="No active emergency incidents." /> : active.map((incident, index) => {
            const id = field(incident, ['id', 'emergency_id']);
            return <Card key={`${id}-${index}`} style={{ marginBottom: 8 }}><Text style={{ fontWeight: '700' }}>Incident {id} · {field(incident, ['status'])}</Text><Text style={{ marginVertical: 5 }}>Patient {field(incident, ['patient_id'])} · {field(incident, ['priority'])}</Text><Text>Location: {field(incident, ['address', 'location', 'description'])}</Text><Button title="View details" variant="secondary" onPress={() => void loadDetails(id)} style={{ marginTop: 8 }} /></Card>;
          })}
          <Button title="Refresh feed" variant="secondary" onPress={() => void refreshActive()} />
        </ScrollView>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingBottom: 16 }}>
          <Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Incident details</Text>
          {!selectedId ? <EmptyState message="Select an incident to see patient and responder details." /> : detailLoading ? <Loader message="Loading incident…" /> : detailError ? <ErrorState message={detailError} onRetry={() => void loadDetails(selectedId)} /> : (
            <>
              <Card style={{ marginBottom: 8 }}>
                <Text style={{ fontWeight: '700' }}>Incident {selectedId} · {field(details, ['status'])}</Text>
                <Text style={{ marginTop: 6 }}>Patient: {field(details, ['patient_name', 'patient_id'])}</Text>
                <Text>Blood group: {field(details, ['blood_group'])}</Text>
                <Text>Allergies: {field(details, ['allergies'])}</Text>
                <Text>Emergency contact: {field(details, ['emergency_contact'])}</Text>
                <Text>Location: {field(details, ['address', 'location'])}</Text>
              </Card>
              <Card style={{ marginBottom: 8 }}><Text style={{ fontWeight: '700', marginBottom: 8 }}>Status timeline</Text>{['acknowledged_at', 'en_route_at', 'arrived_at'].map((key) => <Text key={key} style={{ paddingVertical: 3 }}>{key.split('_').join(' ')}: {field(details, [key])}</Text>)}</Card>
              <View style={{ gap: 8 }}><Button title="Assign responder" onPress={() => setAssignVisible(true)} /><Button title="Mark en route" variant="secondary" disabled={busy} onPress={() => void performAction('status', 'en_route')} /><Button title="Mark arrived" variant="secondary" disabled={busy} onPress={() => void performAction('status', 'arrived')} /></View>
              <Card style={{ marginTop: 8 }}><Text style={{ fontWeight: '700', marginBottom: 6 }}>Responder message</Text><TextInput value={message} onChangeText={setMessage} placeholder="Message patient or responder" multiline style={{ minHeight: 60, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} /><Button title="Send message" disabled={busy} onPress={() => void performAction('message')} /></Card>
              {details && Array.isArray(details.messages) ? <Card style={{ marginTop: 8 }}><Text style={{ fontWeight: '700' }}>Conversation</Text>{details.messages.map((entry, index) => <Text key={index} style={{ paddingVertical: 5 }}>{typeof entry === 'object' && entry !== null && 'message' in entry && typeof entry.message === 'string' ? entry.message : 'Message'}</Text>)}</Card> : null}
            </>
          )}
        </ScrollView>
      </View>
      <Modal visible={assignVisible}><Card><Text style={{ fontSize: 18, fontWeight: '700', marginBottom: 8 }}>Assign responder</Text><TextInput value={responderId} onChangeText={setResponderId} placeholder="Responder ID" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 10 }} /><View style={{ gap: 8 }}><Button title={busy ? 'Assigning…' : 'Assign'} disabled={busy} onPress={() => void performAction('assign')} /><Button title="Cancel" variant="secondary" disabled={busy} onPress={() => setAssignVisible(false)} /></View></Card></Modal>
    </ScreenContainer>
  );
}
