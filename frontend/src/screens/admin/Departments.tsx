import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import {
  NavioraBadge,
  NavioraButton,
  NavioraCard,
  NavioraHeader,
  NavioraText,
} from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { apiService } from '../../services/api';

interface Department {
  id: number;
  name: string;
  description?: string | null;
  floor: number;
  building: string;
  wing: string;
  phone: string;
  email: string;
}

const emptyForm = {
  name: '',
  description: '',
  floor: '',
  building: '',
  wing: '',
  phone: '',
  email: '',
};

const DepartmentsScreen = () => {
  const theme = useTheme();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const loadDepartments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.get<Department[]>('/admin/departments');
      if (response.error || !response.data) {
        setError(response.error || 'Department data is unavailable.');
        return;
      }
      if (!Array.isArray(response.data)) {
        setError('The server returned an invalid department list.');
        return;
      }
      setDepartments(response.data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load departments.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDepartments();
  }, [loadDepartments]);

  const createDepartment = async () => {
    const floor = Number(form.floor);
    if (
      !form.name.trim() || !Number.isInteger(floor) || !form.building.trim() ||
      !form.wing.trim() || !form.phone.trim() || !form.email.trim()
    ) {
      setFormError('Enter a name, whole-number floor, building, wing, phone, and email.');
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      const response = await apiService.post<Department>('/admin/departments', {
        name: form.name.trim(),
        description: form.description.trim() || null,
        floor,
        building: form.building.trim(),
        wing: form.wing.trim(),
        phone: form.phone.trim(),
        email: form.email.trim(),
      });
      if (response.error || !response.data) {
        setFormError(response.error || 'The department was not created.');
        return;
      }
      setDepartments(current => [...current, response.data as Department]);
      setForm(emptyForm);
      setShowForm(false);
    } catch (createError) {
      setFormError(createError instanceof Error ? createError.message : 'Unable to create department.');
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field: keyof typeof emptyForm, value: string) => {
    setForm(current => ({ ...current, [field]: value }));
    setFormError(null);
  };

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <NavioraHeader title="Department Management" subtitle="Floor assignments and services" />
        <TouchableOpacity onPress={() => void loadDepartments()} style={styles.refresh}>
          <NavioraText type="label" color="primary">Refresh departments</NavioraText>
        </TouchableOpacity>
        {loading ? (
          <View style={styles.state}>
            <ActivityIndicator color={theme.colors.primary} />
            <NavioraText type="body" color="secondary" style={styles.stateText}>Loading departments…</NavioraText>
          </View>
        ) : error ? (
          <NavioraCard style={styles.state}>
            <NavioraText type="body" color="error" align="center">{error}</NavioraText>
            <NavioraButton title="Try again" onPress={() => void loadDepartments()} style={styles.stateAction} />
          </NavioraCard>
        ) : departments.length === 0 ? (
          <NavioraCard style={styles.state}>
            <NavioraText type="body" color="secondary" align="center">No departments have been added yet.</NavioraText>
          </NavioraCard>
        ) : departments.map((dept) => (
          <NavioraCard key={dept.id} style={styles.card}>
            <View style={styles.row}>
              <View style={{ flex: 1 }}>
                <NavioraText type="body" style={{ fontWeight: '700' }}>{dept.name}</NavioraText>
                <NavioraText type="caption" color="secondary">
                  Floor {dept.floor} · {dept.building} · {dept.wing}
                </NavioraText>
                {dept.description ? <NavioraText type="caption" color="secondary">{dept.description}</NavioraText> : null}
                <NavioraText type="caption" color="secondary">{dept.phone} · {dept.email}</NavioraText>
              </View>
              <NavioraBadge label={`#${dept.id}`} tone="info" />
            </View>
          </NavioraCard>
        ))}

        <NavioraButton
          title={showForm ? 'Close form' : 'Add Department'}
          icon={showForm ? undefined : 'add-outline'}
          variant="secondary"
          onPress={() => { setShowForm(value => !value); setFormError(null); }}
          style={{ marginTop: 20 }}
        />
        {showForm ? (
          <NavioraCard style={styles.form}>
            <NavioraText type="body" style={styles.formTitle}>New department</NavioraText>
            {([
              ['name', 'Department name'],
              ['description', 'Description (optional)'],
              ['floor', 'Floor number'],
              ['building', 'Building'],
              ['wing', 'Wing'],
              ['phone', 'Phone'],
              ['email', 'Email'],
            ] as const).map(([field, label]) => (
              <TextInput
                key={field}
                value={form[field]}
                onChangeText={value => updateField(field, value)}
                placeholder={label}
                placeholderTextColor={theme.colors.text.secondary}
                keyboardType={field === 'floor' ? 'number-pad' : field === 'phone' ? 'phone-pad' : field === 'email' ? 'email-address' : 'default'}
                autoCapitalize={field === 'email' ? 'none' : 'sentences'}
                style={[styles.input, { color: theme.colors.text.primary, borderColor: theme.colors.border, backgroundColor: theme.colors.surface }]}
              />
            ))}
            {formError ? <NavioraText type="caption" color="error">{formError}</NavioraText> : null}
            <NavioraButton title="Save Department" onPress={() => void createDepartment()} loading={saving} style={styles.saveButton} />
          </NavioraCard>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
};

export default DepartmentsScreen;

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 30 },
  card: { marginTop: 12 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  refresh: { alignSelf: 'flex-end', paddingVertical: 8 },
  state: { marginTop: 16, alignItems: 'center', padding: 20 },
  stateText: { marginTop: 10 },
  stateAction: { marginTop: 14 },
  form: { marginTop: 12, padding: 16 },
  formTitle: { fontWeight: '700', marginBottom: 12 },
  input: { minHeight: 46, borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, marginBottom: 10 },
  saveButton: { marginTop: 12 },
});
