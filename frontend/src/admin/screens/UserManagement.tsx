import React, { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { colors } from '../../shared/theme/colors';
import { Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { useAlert } from '../../context/AlertContext';

type StaffRole = 'doctor' | 'nurse' | 'admin';
type StaffRow = { id: number; first_name?: string | null; last_name?: string | null; email: string; phone: string; role: string; is_active: boolean; created_at?: string };
type Department = { id: number; name: string };
type StaffForm = { first_name: string; last_name: string; email: string; phone: string; password: string; role: StaffRole; department_id: string; specialization: string; license_number: string; years_of_experience: string };
const emptyForm: StaffForm = { first_name: '', last_name: '', email: '', phone: '', password: '', role: 'doctor', department_id: '', specialization: '', license_number: '', years_of_experience: '0' };

function Field({ label, value, onChangeText, placeholder, secureTextEntry, keyboardType }: { label: string; value: string; onChangeText: (value: string) => void; placeholder?: string; secureTextEntry?: boolean; keyboardType?: 'default' | 'email-address' | 'phone-pad' | 'number-pad' }) {
  return <View style={styles.field}><Text style={styles.label}>{label}</Text><TextInput value={value} onChangeText={onChangeText} placeholder={placeholder ?? label} placeholderTextColor={colors.textMuted} secureTextEntry={secureTextEntry} keyboardType={keyboardType} autoCapitalize={keyboardType === 'email-address' ? 'none' : 'words'} style={styles.input} /></View>;
}

export default function UserManagement() {
  const { showAlert } = useAlert();
  const [rows, setRows] = useState<StaffRow[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [form, setForm] = useState<StaffForm>(emptyForm);
  const update = (key: keyof StaffForm, value: string) => setForm(current => ({ ...current, [key]: value }));

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersResponse, departmentsResponse] = await Promise.all([
        apiClient.get<{ items: StaffRow[] }>(buildApiUrl('admin', '/users')),
        apiClient.get<{ items: Department[] }>(buildApiUrl('admin', '/departments')),
      ]);
      setRows(usersResponse.data.items ?? []);
      setDepartments(departmentsResponse.data.items ?? []);
    } catch {
      setError('Could not load users or departments.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const createStaff = async () => {
    if (!form.first_name.trim() || !form.last_name.trim() || !form.email.trim() || !form.phone.trim() || form.password.length < 12) {
      showAlert('Enter names, email, phone, and a password of at least 12 characters.', 'warning');
      return;
    }
    if (form.role === 'doctor' && (!form.department_id || !form.specialization.trim() || !form.license_number.trim())) {
      showAlert('Doctors need a department, specialization, and license number.', 'warning');
      return;
    }
    const payload = {
      first_name: form.first_name.trim(), last_name: form.last_name.trim(), email: form.email.trim(), phone: form.phone.trim(), password: form.password, role: form.role,
      ...(form.role !== 'admin' && form.department_id ? { department_id: Number(form.department_id) } : {}),
      ...(form.role === 'doctor' ? { specialization: form.specialization.trim(), license_number: form.license_number.trim(), years_of_experience: Number(form.years_of_experience) || 0 } : {}),
    };
    setSaving(true);
    try {
      await apiClient.post(buildApiUrl('admin', '/users'), payload);
      setVisible(false);
      setForm(emptyForm);
      showAlert('Staff account created successfully.', 'success');
      await load();
    } catch (cause) {
      const message = isAxiosError(cause) ? String(cause.response?.data?.detail ?? 'Could not create this account.') : 'Could not create this account.';
      showAlert(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return <ScreenContainer>
    <SectionHeader title="Users" />
    <Text style={styles.description}>Hospital accounts, roles, and account state</Text>
    <View style={styles.actions}><Button title="Create Staff" onPress={() => setVisible(true)} /><Button title="Refresh" variant="secondary" onPress={() => void load()} /></View>
    {loading ? <Loader message="Loading users…" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : rows.length === 0 ? <EmptyState message="No user records are available." /> : <ScrollView contentContainerStyle={styles.list}>
      {rows.map(user => <Card key={user.id} style={styles.userCard}>
        <Text style={styles.userName}>{[user.first_name, user.last_name].filter(Boolean).join(' ') || user.email}</Text>
        <Text style={styles.userDetail}>{user.email} · {user.phone}</Text>
        <Text style={styles.userRole}>{user.role} · {user.is_active ? 'Active' : 'Inactive'}</Text>
      </Card>)}
    </ScrollView>}

    <Modal visible={visible} animationType="slide" transparent onRequestClose={() => setVisible(false)}>
      <View style={styles.overlay}><View style={styles.modal}>
        <View style={styles.modalHeader}><Text style={styles.modalTitle}>Create Staff Account</Text><Pressable accessibilityRole="button" onPress={() => setVisible(false)}><Text style={styles.close}>Close</Text></Pressable></View>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.form}>
          <Field label="First name" value={form.first_name} onChangeText={value => update('first_name', value)} />
          <Field label="Last name" value={form.last_name} onChangeText={value => update('last_name', value)} />
          <Field label="Email" value={form.email} onChangeText={value => update('email', value)} keyboardType="email-address" />
          <Field label="Phone" value={form.phone} onChangeText={value => update('phone', value)} keyboardType="phone-pad" />
          <Field label="Temporary password (12+ characters)" value={form.password} onChangeText={value => update('password', value)} secureTextEntry />
          <Text style={styles.label}>Role</Text>
          <View style={styles.roles}>{(['doctor', 'nurse', 'admin'] as StaffRole[]).map(role => <Pressable key={role} onPress={() => update('role', role)} style={[styles.roleButton, form.role === role && styles.roleSelected]}><Text style={[styles.roleText, form.role === role && styles.roleTextSelected]}>{role}</Text></Pressable>)}</View>
          {form.role === 'doctor' && <>
            <Text style={styles.label}>Department</Text>
            {departments.length ? <View style={styles.departmentList}>{departments.map(department => <Pressable key={department.id} onPress={() => update('department_id', String(department.id))} style={[styles.roleButton, form.department_id === String(department.id) && styles.roleSelected]}><Text style={[styles.roleText, form.department_id === String(department.id) && styles.roleTextSelected]}>{department.name}</Text></Pressable>)}</View> : <Text style={styles.hint}>Create a department before adding a doctor.</Text>}
            <Field label="Specialization" value={form.specialization} onChangeText={value => update('specialization', value)} />
            <Field label="License number" value={form.license_number} onChangeText={value => update('license_number', value)} />
            <Field label="Years of experience" value={form.years_of_experience} onChangeText={value => update('years_of_experience', value)} keyboardType="number-pad" />
          </>}
          {form.role === 'nurse' && <>
            <Text style={styles.label}>Department (optional)</Text>
            <View style={styles.departmentList}><Pressable onPress={() => update('department_id', '')} style={[styles.roleButton, !form.department_id && styles.roleSelected]}><Text style={[styles.roleText, !form.department_id && styles.roleTextSelected]}>None</Text></Pressable>{departments.map(department => <Pressable key={department.id} onPress={() => update('department_id', String(department.id))} style={[styles.roleButton, form.department_id === String(department.id) && styles.roleSelected]}><Text style={[styles.roleText, form.department_id === String(department.id) && styles.roleTextSelected]}>{department.name}</Text></Pressable>)}</View>
          </>}
          <Button title="Create Account" loading={saving} disabled={saving || (form.role === 'doctor' && departments.length === 0)} onPress={() => void createStaff()} style={styles.submit} />
        </ScrollView>
      </View></View>
    </Modal>
  </ScreenContainer>;
}

const styles = StyleSheet.create({
  description: { color: colors.textMuted, marginBottom: 12 },
  actions: { flexDirection: 'row', gap: 10, marginBottom: 8 },
  list: { paddingBottom: 24 },
  userCard: { marginTop: 10 },
  userName: { color: colors.text, fontSize: 16, fontWeight: '700' },
  userDetail: { color: colors.textMuted, marginTop: 4 },
  userRole: { color: colors.primary, marginTop: 6, textTransform: 'capitalize', fontWeight: '600' },
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' },
  modal: { maxHeight: '92%', backgroundColor: colors.background, borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  modalTitle: { color: colors.text, fontSize: 19, fontWeight: '700' },
  close: { color: colors.primary, fontWeight: '700', padding: 8 },
  form: { paddingBottom: 28 },
  field: { marginBottom: 12 },
  label: { color: colors.text, fontWeight: '600', marginBottom: 6 },
  input: { backgroundColor: colors.white, borderColor: colors.border, borderWidth: 1, borderRadius: 10, color: colors.text, paddingHorizontal: 12, paddingVertical: 11 },
  roles: { flexDirection: 'row', gap: 8, marginBottom: 12, marginTop: 2 },
  departmentList: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12, marginTop: 2 },
  roleButton: { borderWidth: 1, borderColor: colors.border, borderRadius: 18, paddingHorizontal: 13, paddingVertical: 8, backgroundColor: colors.white },
  roleSelected: { borderColor: colors.primary, backgroundColor: colors.primary },
  roleText: { color: colors.text, textTransform: 'capitalize' },
  roleTextSelected: { color: colors.white },
  hint: { color: colors.warning, marginBottom: 12 },
  submit: { marginTop: 8 },
});
