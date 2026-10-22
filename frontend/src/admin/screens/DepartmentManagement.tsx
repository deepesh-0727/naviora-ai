import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { isAxiosError } from 'axios';
import { colors } from '../../shared/theme/colors';
import { Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { useAlert } from '../../context/AlertContext';

type Department = { id: number; name: string; description?: string | null; floor: number; building: string; wing: string; phone: string; email: string };
type DepartmentForm = { name: string; description: string; floor: string; building: string; wing: string; phone: string; email: string };
const emptyForm: DepartmentForm = { name: '', description: '', floor: '0', building: '', wing: '', phone: '', email: '' };

function Field({ label, value, onChangeText, keyboardType = 'default' }: { label: string; value: string; onChangeText: (value: string) => void; keyboardType?: 'default' | 'email-address' | 'phone-pad' | 'number-pad' }) {
  return <View style={styles.field}><Text style={styles.label}>{label}</Text><TextInput value={value} onChangeText={onChangeText} keyboardType={keyboardType} autoCapitalize={keyboardType === 'email-address' ? 'none' : 'sentences'} placeholder={label} placeholderTextColor={colors.textMuted} style={styles.input} /></View>;
}

export default function DepartmentManagement() {
  const { showAlert } = useAlert();
  const [rows, setRows] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [editing, setEditing] = useState<Department | null>(null);
  const [form, setForm] = useState<DepartmentForm>(emptyForm);
  const update = (key: keyof DepartmentForm, value: string) => setForm(current => ({ ...current, [key]: value }));

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<{ items: Department[] }>(buildApiUrl('admin', '/departments'));
      setRows(response.data.items ?? []);
    } catch {
      setError('Could not load departments.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const openCreate = () => { setEditing(null); setForm(emptyForm); setVisible(true); };
  const openEdit = (department: Department) => {
    setEditing(department);
    setForm({ name: department.name, description: department.description ?? '', floor: String(department.floor), building: department.building, wing: department.wing, phone: department.phone, email: department.email });
    setVisible(true);
  };

  const save = async () => {
    if (!form.name.trim() || !form.building.trim() || !form.wing.trim() || !form.phone.trim() || !form.email.trim() || !Number.isInteger(Number(form.floor))) {
      showAlert('Complete all required department fields and enter a whole-number floor.', 'warning');
      return;
    }
    setSaving(true);
    try {
      const payload = { name: form.name.trim(), description: form.description.trim() || null, floor: Number(form.floor), building: form.building.trim(), wing: form.wing.trim(), phone: form.phone.trim(), email: form.email.trim() };
      if (editing) await apiClient.put(buildApiUrl('admin', `/departments/${editing.id}`), payload);
      else await apiClient.post(buildApiUrl('admin', '/departments'), payload);
      setVisible(false);
      showAlert(editing ? 'Department updated.' : 'Department created.', 'success');
      await load();
    } catch (cause) {
      showAlert(isAxiosError(cause) ? String(cause.response?.data?.detail ?? 'Could not save this department.') : 'Could not save this department.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const remove = (department: Department) => Alert.alert('Delete department?', `Delete ${department.name}?`, [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: () => { void (async () => {
      try {
        await apiClient.delete(buildApiUrl('admin', `/departments/${department.id}`));
        showAlert('Department deleted.', 'success');
        await load();
      } catch (cause) {
        showAlert(isAxiosError(cause) ? String(cause.response?.data?.detail ?? 'Could not delete this department.') : 'Could not delete this department.', 'error');
      }
    })(); } },
  ]);

  return <ScreenContainer>
    <SectionHeader title="Departments" />
    <Text style={styles.description}>Manage hospital departments and contact details.</Text>
    <View style={styles.actions}><Button title="Create Department" onPress={openCreate} /><Button title="Refresh" variant="secondary" onPress={() => void load()} /></View>
    {loading ? <Loader message="Loading departments…" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : rows.length === 0 ? <EmptyState message="No departments are available." /> : <ScrollView contentContainerStyle={styles.list}>
      {rows.map(department => <Card key={department.id} style={styles.card}>
        <Text style={styles.name}>{department.name}</Text>
        <Text style={styles.detail}>{department.building} · {department.wing} · Floor {department.floor}</Text>
        <Text style={styles.detail}>{department.phone} · {department.email}</Text>
        {department.description ? <Text style={styles.detail}>{department.description}</Text> : null}
        <View style={styles.actions}><Button title="Edit" variant="secondary" onPress={() => openEdit(department)} /><Button title="Delete" variant="danger" onPress={() => remove(department)} /></View>
      </Card>)}
    </ScrollView>}

    <Modal visible={visible} animationType="slide" transparent onRequestClose={() => setVisible(false)}>
      <View style={styles.overlay}><View style={styles.modal}>
        <View style={styles.modalHeader}><Text style={styles.modalTitle}>{editing ? 'Edit Department' : 'Create Department'}</Text><Pressable accessibilityRole="button" onPress={() => setVisible(false)}><Text style={styles.close}>Close</Text></Pressable></View>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.form}>
          <Field label="Name" value={form.name} onChangeText={value => update('name', value)} />
          <Field label="Floor" value={form.floor} onChangeText={value => update('floor', value)} keyboardType="number-pad" />
          <Field label="Building" value={form.building} onChangeText={value => update('building', value)} />
          <Field label="Wing" value={form.wing} onChangeText={value => update('wing', value)} />
          <Field label="Phone" value={form.phone} onChangeText={value => update('phone', value)} keyboardType="phone-pad" />
          <Field label="Email" value={form.email} onChangeText={value => update('email', value)} keyboardType="email-address" />
          <Field label="Description (optional)" value={form.description} onChangeText={value => update('description', value)} />
          <Button title={editing ? 'Save Changes' : 'Create Department'} loading={saving} disabled={saving} onPress={() => void save()} style={styles.submit} />
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
  name: { color: colors.text, fontSize: 16, fontWeight: '700' },
  detail: { color: colors.textMuted, marginTop: 5 },
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' },
  modal: { maxHeight: '92%', backgroundColor: colors.background, borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  modalTitle: { color: colors.text, fontSize: 19, fontWeight: '700' },
  close: { color: colors.primary, fontWeight: '700', padding: 8 },
  form: { paddingBottom: 28 },
  field: { marginBottom: 12 },
  label: { color: colors.text, fontWeight: '600', marginBottom: 6 },
  input: { backgroundColor: colors.white, borderColor: colors.border, borderWidth: 1, borderRadius: 10, color: colors.text, paddingHorizontal: 12, paddingVertical: 11 },
  submit: { marginTop: 8 },
});
