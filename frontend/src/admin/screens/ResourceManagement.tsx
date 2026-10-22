import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { isAxiosError } from 'axios';
import { colors } from '../../shared/theme/colors';
import { Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { useAlert } from '../../context/AlertContext';

type BedStatus = 'available' | 'occupied' | 'cleaning' | 'maintenance' | 'reserved' | 'critical';
type Bed = { id: number; bed_number: string; ward: string; floor: number; status: BedStatus; patient_id?: number | null };
type BedForm = { bed_number: string; ward: string; floor: string; status: BedStatus };
const emptyForm: BedForm = { bed_number: '', ward: '', floor: '0', status: 'available' };
const statuses: BedStatus[] = ['available', 'cleaning', 'maintenance', 'reserved', 'occupied', 'critical'];

function Field({ label, value, onChangeText, keyboardType = 'default' }: { label: string; value: string; onChangeText: (value: string) => void; keyboardType?: 'default' | 'number-pad' }) {
  return <View style={styles.field}><Text style={styles.label}>{label}</Text><TextInput value={value} onChangeText={onChangeText} keyboardType={keyboardType} placeholder={label} placeholderTextColor={colors.textMuted} style={styles.input} /></View>;
}

export default function ResourceManagement() {
  const { showAlert } = useAlert();
  const [rows, setRows] = useState<Bed[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [editing, setEditing] = useState<Bed | null>(null);
  const [form, setForm] = useState<BedForm>(emptyForm);
  const update = (key: keyof BedForm, value: string) => setForm(current => ({ ...current, [key]: value }));

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<{ items: Bed[] }>(buildApiUrl('admin', '/resources/beds'));
      setRows(response.data.items ?? []);
    } catch {
      setError('Could not load beds.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const openCreate = () => { setEditing(null); setForm(emptyForm); setVisible(true); };
  const openEdit = (bed: Bed) => { setEditing(bed); setForm({ bed_number: bed.bed_number, ward: bed.ward, floor: String(bed.floor), status: bed.status }); setVisible(true); };

  const save = async () => {
    if (!form.bed_number.trim() || !form.ward.trim() || !Number.isInteger(Number(form.floor))) {
      showAlert('Enter a bed number, ward, and whole-number floor.', 'warning');
      return;
    }
    if (!editing && ['occupied', 'critical'].includes(form.status)) {
      showAlert('A new bed must be available, cleaning, or reserved until assigned to a patient.', 'warning');
      return;
    }
    setSaving(true);
    try {
      const payload = { bed_number: form.bed_number.trim(), ward: form.ward.trim(), floor: Number(form.floor), status: form.status };
      if (editing) await apiClient.put(buildApiUrl('admin', `/resources/beds/${editing.id}`), payload);
      else await apiClient.post(buildApiUrl('admin', '/resources/beds'), payload);
      setVisible(false);
      showAlert(editing ? 'Bed updated.' : 'Bed created.', 'success');
      await load();
    } catch (cause) {
      showAlert(isAxiosError(cause) ? String(cause.response?.data?.detail ?? 'Could not save this bed.') : 'Could not save this bed.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const remove = (bed: Bed) => Alert.alert('Delete bed?', `Delete bed ${bed.bed_number} in ${bed.ward}?`, [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: () => { void (async () => {
      try {
        await apiClient.delete(buildApiUrl('admin', `/resources/beds/${bed.id}`));
        showAlert('Bed deleted.', 'success');
        await load();
      } catch (cause) {
        showAlert(isAxiosError(cause) ? String(cause.response?.data?.detail ?? 'Could not delete this bed.') : 'Could not delete this bed.', 'error');
      }
    })(); } },
  ]);

  return <ScreenContainer>
    <SectionHeader title="Beds" />
    <Text style={styles.description}>Manage bed numbers, wards, floors, and availability.</Text>
    <View style={styles.actions}><Button title="Create Bed" onPress={openCreate} /><Button title="Refresh" variant="secondary" onPress={() => void load()} /></View>
    {loading ? <Loader message="Loading beds…" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : rows.length === 0 ? <EmptyState message="No beds are available." /> : <ScrollView contentContainerStyle={styles.list}>
      {rows.map(bed => <Card key={bed.id} style={styles.card}>
        <Text style={styles.name}>Bed {bed.bed_number}</Text>
        <Text style={styles.detail}>{bed.ward} · Floor {bed.floor} · {bed.status}</Text>
        {bed.patient_id ? <Text style={styles.detail}>Patient ID: {bed.patient_id}</Text> : null}
        <View style={styles.actions}><Button title="Edit" variant="secondary" onPress={() => openEdit(bed)} /><Button title="Delete" variant="danger" disabled={Boolean(bed.patient_id) || ['occupied', 'critical'].includes(bed.status)} onPress={() => remove(bed)} /></View>
      </Card>)}
    </ScrollView>}

    <Modal visible={visible} animationType="slide" transparent onRequestClose={() => setVisible(false)}>
      <View style={styles.overlay}><View style={styles.modal}>
        <View style={styles.modalHeader}><Text style={styles.modalTitle}>{editing ? 'Edit Bed' : 'Create Bed'}</Text><Pressable accessibilityRole="button" onPress={() => setVisible(false)}><Text style={styles.close}>Close</Text></Pressable></View>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.form}>
          <Field label="Bed number" value={form.bed_number} onChangeText={value => update('bed_number', value)} />
          <Field label="Ward" value={form.ward} onChangeText={value => update('ward', value)} />
          <Field label="Floor" value={form.floor} onChangeText={value => update('floor', value)} keyboardType="number-pad" />
          <Text style={styles.label}>Status</Text>
          <View style={styles.statuses}>{statuses.map(status => <Pressable key={status} onPress={() => update('status', status)} style={[styles.statusButton, form.status === status && styles.statusSelected]}><Text style={[styles.statusText, form.status === status && styles.statusTextSelected]}>{status}</Text></Pressable>)}</View>
          <Button title={editing ? 'Save Changes' : 'Create Bed'} loading={saving} disabled={saving} onPress={() => void save()} style={styles.submit} />
        </ScrollView>
      </View></View>
    </Modal>
  </ScreenContainer>;
}

const styles = StyleSheet.create({
  description: { color: colors.textMuted, marginBottom: 12 },
  actions: { flexDirection: 'row', gap: 8, marginTop: 8, flexWrap: 'wrap' },
  list: { paddingBottom: 24 },
  card: { marginTop: 10 },
  name: { color: colors.text, fontSize: 16, fontWeight: '700', textTransform: 'capitalize' },
  detail: { color: colors.textMuted, marginTop: 5, textTransform: 'capitalize' },
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' },
  modal: { maxHeight: '92%', backgroundColor: colors.background, borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  modalTitle: { color: colors.text, fontSize: 19, fontWeight: '700' },
  close: { color: colors.primary, fontWeight: '700', padding: 8 },
  form: { paddingBottom: 28 },
  field: { marginBottom: 12 },
  label: { color: colors.text, fontWeight: '600', marginBottom: 6, textTransform: 'capitalize' },
  input: { backgroundColor: colors.white, borderColor: colors.border, borderWidth: 1, borderRadius: 10, color: colors.text, paddingHorizontal: 12, paddingVertical: 11 },
  statuses: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  statusButton: { borderWidth: 1, borderColor: colors.border, borderRadius: 18, paddingHorizontal: 13, paddingVertical: 8, backgroundColor: colors.white },
  statusSelected: { borderColor: colors.primary, backgroundColor: colors.primary },
  statusText: { color: colors.text, textTransform: 'capitalize' },
  statusTextSelected: { color: colors.white },
  submit: { marginTop: 8 },
});
