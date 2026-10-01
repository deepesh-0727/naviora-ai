import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { NavioraButton, NavioraCard, NavioraHeader, NavioraInput, NavioraText } from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { apiService } from '../../services/api';

export default function DoctorPrescriptionScreen({ navigation, route }: any) {
  const theme = useTheme();
  const patientId = route?.params?.patient?.id;
  const [form, setForm] = useState({ medication: '', dosage: '', frequency: '', duration: '', instructions: '', quantity: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!patientId || !form.medication || !form.dosage || !form.frequency || !form.duration || !form.quantity) {
      setError('Patient, medication, dosage, frequency, duration, and quantity are required.');
      return;
    }
    setLoading(true);
    setError('');
    const result = await apiService.post('/pharmacy/prescriptions', {
      patient_id: patientId,
      medication_name: form.medication,
      dosage: form.dosage,
      frequency: form.frequency,
      duration: form.duration,
      instructions: form.instructions,
      quantity: Number(form.quantity),
    });
    setLoading(false);
    if (result.data) navigation.goBack();
    else setError(result.error || 'Unable to save prescription.');
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }} contentContainerStyle={styles.content}>
      <NavioraHeader title="Write Prescription" subtitle="Medication, dosage and instructions" />
      {!patientId && <NavioraText color="danger" style={styles.error}>Open this screen from a patient record.</NavioraText>}
      <NavioraCard style={styles.card}>
        <NavioraInput label="Medication" value={form.medication} onChangeText={(v: string) => setForm({ ...form, medication: v })} icon="medical-outline" />
        <NavioraInput label="Dosage" value={form.dosage} onChangeText={(v: string) => setForm({ ...form, dosage: v })} icon="flask-outline" />
        <NavioraInput label="Frequency" value={form.frequency} onChangeText={(v: string) => setForm({ ...form, frequency: v })} icon="repeat-outline" />
        <NavioraInput label="Duration" value={form.duration} onChangeText={(v: string) => setForm({ ...form, duration: v })} icon="calendar-outline" />
        <NavioraInput label="Instructions" value={form.instructions} onChangeText={(v: string) => setForm({ ...form, instructions: v })} icon="document-text-outline" />
        <NavioraInput label="Quantity" value={form.quantity} onChangeText={(v: string) => setForm({ ...form, quantity: v })} keyboardType="number-pad" icon="layers-outline" />
        {error ? <NavioraText color="danger" style={styles.error}>{error}</NavioraText> : null}
        <NavioraButton title={loading ? 'Saving...' : 'Send to Pharmacy'} onPress={submit} disabled={loading} icon="send-outline" />
      </NavioraCard>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, paddingBottom: 40 },
  card: { marginTop: 12, padding: 16 },
  error: { marginVertical: 12 },
});
