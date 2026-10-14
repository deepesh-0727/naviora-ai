import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, Text, TextInput, View } from 'react-native';
import { useRoute, type RouteProp } from '@react-navigation/native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, Modal, ScreenContainer, Tabs } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';
import { usePatientRecord, type PatientRecordSection } from '../hooks/usePatientRecord';

type DetailRoute = RouteProp<{ PatientDetail: { patientId?: string | number } }, 'PatientDetail'>;
type RecordTab = 'Overview' | 'History' | 'Vitals' | 'Labs' | 'Prescriptions' | 'Notes';
type ActionKind = 'prescription' | 'lab-order' | 'referral' | 'admission';
const TABS: RecordTab[] = ['Overview', 'History', 'Vitals', 'Labs', 'Prescriptions', 'Notes'];
const ACTIONS: { kind: ActionKind; label: string; path: string }[] = [
  { kind: 'prescription', label: 'New prescription', path: '/prescriptions' },
  { kind: 'lab-order', label: 'Order lab', path: '/lab-orders' },
  { kind: 'referral', label: 'Create referral', path: '/referrals' },
  { kind: 'admission', label: 'Admit patient', path: '/admissions' },
];

function entries(value: PatientRecordSection): Array<[string, string]> {
  return Object.entries(value).filter(([, field]) => field === null || ['string', 'number', 'boolean'].includes(typeof field))
    .map(([key, field]) => [key.split('_').join(' '), field === null ? '—' : String(field)]);
}

function RecordList({ data, emptyMessage }: { data: PatientRecordSection[]; emptyMessage: string }) {
  if (data.length === 0) return <EmptyState message={emptyMessage} />;
  return <View style={{ gap: 10 }}>{data.map((item, index) => (
    <Card key={String(item.id ?? index)}>{entries(item).map(([label, value]) => <Text key={label} style={{ paddingVertical: 3 }}>{label}: {value}</Text>)}</Card>
  ))}</View>;
}

export default function PatientDetail() {
  const route = useRoute<DetailRoute>();
  const patientId = route.params?.patientId;
  const { record, loading, error, backendUnavailable, empty, refresh } = usePatientRecord(patientId);
  const [activeTab, setActiveTab] = useState<RecordTab>('Overview');
  const [action, setAction] = useState<ActionKind | null>(null);
  const [formValue, setFormValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const reload = useCallback(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    void websocketClient.connect();
    const unsubscribePrescription = websocketClient.subscribe('prescription_submitted', reload);
    const unsubscribeLab = websocketClient.subscribe('lab_report_ready', reload);
    return () => { unsubscribePrescription(); unsubscribeLab(); };
  }, [reload]);

  const submitAction = async () => {
    if (!patientId || !action || !formValue.trim()) {
      setActionError('Enter the required details before submitting.');
      return;
    }
    const actionConfig = ACTIONS.find((item) => item.kind === action);
    if (!actionConfig) return;
    setSaving(true);
    setActionError(null);
    setActionMessage(null);
    try {
      await apiClient.post(buildApiUrl('doctor', `/patients/${encodeURIComponent(String(patientId))}${actionConfig.path}`), {
        details: formValue.trim(),
      });
      setActionMessage(`${actionConfig.label} submitted.`);
      setAction(null);
      setFormValue('');
      await refresh();
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason
        ? (reason as { response?: { status?: number } }).response?.status
        : undefined;
      setActionError(status === 404 || status === 501 ? 'This action is not available on the backend yet.' : 'Could not submit this request. Retry when the service is available.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Loader message="Loading patient record…" />;
  if (backendUnavailable) return <ScreenContainer><BackendNotAvailable endpoint="GET /staff/patients/{id}" /><Button title="Retry" variant="secondary" onPress={reload} /></ScreenContainer>;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (empty) return <ScreenContainer><EmptyState message="Patient record is unavailable. Open this screen from a patient list." /><Button title="Retry" variant="secondary" onPress={reload} /></ScreenContainer>;

  const sections: Record<RecordTab, PatientRecordSection[]> = {
    Overview: record.patient ? [record.patient] : [],
    History: record.history,
    Vitals: record.vitals,
    Labs: record.labs,
    Prescriptions: record.prescriptions,
    Notes: record.history.filter((item) => 'note' in item || 'notes' in item),
  };

  return (
    <ScreenContainer>
      <Text style={{ fontSize: 22, fontWeight: '700', marginBottom: 12 }}>Patient record</Text>
      <Tabs items={TABS} activeIndex={TABS.indexOf(activeTab)} onChange={(index) => setActiveTab(TABS[index])} />
      {actionMessage ? <Text accessibilityRole="alert" style={{ color: '#1D8A6C', marginVertical: 8 }}>{actionMessage}</Text> : null}
      {actionError ? <Text accessibilityRole="alert" style={{ color: '#B42318', marginVertical: 8 }}>{actionError}</Text> : null}
      <ScrollView style={{ flex: 1, marginVertical: 12 }} contentContainerStyle={{ paddingBottom: 16 }}>
        <RecordList data={sections[activeTab]} emptyMessage={`No ${activeTab.toLowerCase()} available for this patient.`} />
      </ScrollView>
      {activeTab === 'Prescriptions' ? (
        <Button title="Create prescription" onPress={() => { setAction('prescription'); setActionError(null); }} />
      ) : activeTab === 'Labs' ? (
        <Button title="Order lab test" onPress={() => { setAction('lab-order'); setActionError(null); }} />
      ) : activeTab === 'Overview' ? (
        <View style={{ gap: 8 }}>
          {ACTIONS.filter((item) => item.kind === 'referral' || item.kind === 'admission').map((item) => <Button key={item.kind} title={item.label} variant="secondary" onPress={() => { setAction(item.kind); setActionError(null); }} />)}
        </View>
      ) : null}
      <Modal visible={action !== null}>
        <Card>
          <Text style={{ fontWeight: '700', fontSize: 18, marginBottom: 10 }}>{ACTIONS.find((item) => item.kind === action)?.label ?? 'Patient action'}</Text>
          <TextInput value={formValue} onChangeText={setFormValue} placeholder="Enter clinical details" multiline style={{ minHeight: 96, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 12, marginBottom: 12 }} />
          <View style={{ gap: 8 }}>
            <Button title={saving ? 'Submitting…' : 'Submit'} disabled={saving} onPress={() => void submitAction()} />
            <Button title="Cancel" variant="secondary" disabled={saving} onPress={() => setAction(null)} />
          </View>
        </Card>
      </Modal>
    </ScreenContainer>
  );
}
