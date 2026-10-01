import React, { useState } from 'react';
import { SafeAreaView, ScrollView, StyleSheet } from 'react-native';
import { NavioraButton, NavioraCard, NavioraHeader, NavioraInput, NavioraText } from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { apiService } from '../../services/api';

export default function NurseVitalsScreen({ route, navigation }: any) {
  const theme = useTheme();
  const patientId = route?.params?.patientId || route?.params?.patient?.id;
  const [form, setForm] = useState({ systolic: '', diastolic: '', heart_rate: '', temperature: '', spo2: '', weight: '', height: '', notes: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const update = (key: keyof typeof form, value: string) => setForm(current => ({ ...current, [key]: value }));

  const submit = async () => {
    if (!patientId || !form.systolic || !form.diastolic || !form.heart_rate || !form.temperature || !form.spo2) {
      setError('Patient and core vital readings are required.');
      return;
    }
    setLoading(true);
    setError('');
    const result = await apiService.post('/patients/vitals', {
      patient_id: patientId,
      blood_pressure_systolic: Number(form.systolic),
      blood_pressure_diastolic: Number(form.diastolic),
      heart_rate: Number(form.heart_rate),
      temperature: Number(form.temperature),
      spo2: Number(form.spo2),
      weight: form.weight ? Number(form.weight) : undefined,
      height: form.height ? Number(form.height) : undefined,
      notes: form.notes,
    });
    setLoading(false);
    if (result.data) navigation.goBack();
    else setError(result.error || 'Unable to save vitals.');
  };

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <NavioraHeader title="Vitals Entry" subtitle="Record current patient readings" />
        <NavioraCard style={styles.card}>
          <NavioraInput label="Systolic BP" value={form.systolic} onChangeText={(v: string) => update('systolic', v)} keyboardType="number-pad" icon="pulse-outline" />
          <NavioraInput label="Diastolic BP" value={form.diastolic} onChangeText={(v: string) => update('diastolic', v)} keyboardType="number-pad" icon="pulse-outline" />
          <NavioraInput label="Heart rate" value={form.heart_rate} onChangeText={(v: string) => update('heart_rate', v)} keyboardType="number-pad" icon="heart-outline" />
          <NavioraInput label="Temperature" value={form.temperature} onChangeText={(v: string) => update('temperature', v)} keyboardType="decimal-pad" icon="thermometer-outline" />
          <NavioraInput label="SpO2" value={form.spo2} onChangeText={(v: string) => update('spo2', v)} keyboardType="number-pad" icon="fitness-outline" />
          <NavioraInput label="Weight (kg)" value={form.weight} onChangeText={(v: string) => update('weight', v)} keyboardType="decimal-pad" icon="barbell-outline" />
          <NavioraInput label="Height (cm)" value={form.height} onChangeText={(v: string) => update('height', v)} keyboardType="decimal-pad" icon="resize-outline" />
          <NavioraInput label="Notes" value={form.notes} onChangeText={(v: string) => update('notes', v)} icon="document-text-outline" />
          {error ? <NavioraText color="danger" style={styles.error}>{error}</NavioraText> : null}
          <NavioraButton title={loading ? 'Saving...' : 'Save Vitals'} icon="save-outline" onPress={submit} disabled={loading} />
        </NavioraCard>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 30 },
  card: { marginTop: 12, padding: 16 },
  error: { marginBottom: 12 },
});
