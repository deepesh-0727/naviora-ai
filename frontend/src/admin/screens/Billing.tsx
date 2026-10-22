import React, { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { Alert, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useAlert } from '../../context/AlertContext';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type Invoice = { id: number; patient_id: number; amount: number | string; status: string; invoice_number: string; created_at?: string };
type InvoiceForm = { patient_id: string; amount: string; status: 'pending' | 'cancelled' };
const blankForm: InvoiceForm = { patient_id: '', amount: '', status: 'pending' };

export default function Billing() {
  const { showAlert } = useAlert();
  const [rows, setRows] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [form, setForm] = useState<InvoiceForm>(blankForm);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<{ items: Invoice[] }>(buildApiUrl('admin', '/billing/bills'));
      setRows(response.data.items ?? []);
    } catch {
      setError('Could not load billing records.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const createInvoice = async () => {
    const patientId = Number(form.patient_id);
    const amount = Number(form.amount);
    if (!Number.isInteger(patientId) || patientId < 1 || !Number.isFinite(amount) || amount <= 0) {
      showAlert('Enter a valid patient ID and an amount greater than zero.', 'warning');
      return;
    }
    setSaving(true);
    try {
      await apiClient.post(buildApiUrl('admin', '/billing/invoices'), { patient_id: patientId, amount: amount.toFixed(2), status: form.status });
      setVisible(false);
      setForm(blankForm);
      showAlert('Invoice created successfully.', 'success');
      await load();
    } catch (cause) {
      const message = isAxiosError(cause) ? String(cause.response?.data?.detail ?? 'Could not create this invoice.') : 'Could not create this invoice.';
      showAlert(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return <ScreenContainer>
    <SectionHeader title="Billing" />
    <Text style={styles.description}>Invoices and payment status</Text>
    <View style={styles.actions}>
      <Button title="Create Invoice" onPress={() => { setForm(blankForm); setVisible(true); }} />
      <Button title="Refresh" variant="secondary" onPress={() => void load()} />
    </View>
    {loading ? <Loader message="Loading billing records…" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : rows.length === 0 ? <EmptyState message="No billing records are available." /> : <ScrollView contentContainerStyle={styles.list}>
      {rows.map(invoice => <Card key={invoice.id} style={styles.card}>
        <Text style={styles.invoiceNumber}>{invoice.invoice_number}</Text>
        <Text style={styles.detail}>Patient ID {invoice.patient_id} · ₹{Number(invoice.amount).toFixed(2)}</Text>
        <Text style={styles.status}>{invoice.status}</Text>
        {invoice.created_at ? <Text style={styles.detail}>{new Date(invoice.created_at).toLocaleDateString()}</Text> : null}
      </Card>)}
    </ScrollView>}

    <Modal visible={visible} animationType="slide" transparent onRequestClose={() => setVisible(false)}>
      <View style={styles.overlay}><View style={styles.modal}>
        <View style={styles.modalHeader}><Text style={styles.modalTitle}>Create Invoice</Text><Pressable accessibilityRole="button" onPress={() => setVisible(false)}><Text style={styles.close}>Close</Text></Pressable></View>
        <Text style={styles.label}>Patient ID</Text>
        <TextInput value={form.patient_id} onChangeText={patient_id => setForm(current => ({ ...current, patient_id }))} keyboardType="number-pad" placeholder="Patient ID" placeholderTextColor={colors.textMuted} style={styles.input} />
        <Text style={styles.label}>Amount (INR)</Text>
        <TextInput value={form.amount} onChangeText={amount => setForm(current => ({ ...current, amount }))} keyboardType="decimal-pad" placeholder="Amount" placeholderTextColor={colors.textMuted} style={styles.input} />
        <Text style={styles.label}>Status</Text>
        <View style={styles.statuses}>{(['pending', 'cancelled'] as const).map(status => <Pressable key={status} accessibilityRole="button" onPress={() => setForm(current => ({ ...current, status }))} style={[styles.statusOption, form.status === status && styles.statusSelected]}><Text style={[styles.statusText, form.status === status && styles.statusTextSelected]}>{status}</Text></Pressable>)}</View>
        <Text style={styles.note}>Paid status is applied through the payment flow after payment is received.</Text>
        <Button title="Create Invoice" loading={saving} disabled={saving} onPress={() => void createInvoice()} style={styles.submit} />
      </View></View>
    </Modal>
  </ScreenContainer>;
}

const styles = StyleSheet.create({
  description: { color: colors.textMuted, marginBottom: 10 },
  actions: { flexDirection: 'row', gap: 8, marginBottom: 8, flexWrap: 'wrap' },
  list: { paddingBottom: 24 },
  card: { marginTop: 10 },
  invoiceNumber: { color: colors.text, fontWeight: '700', fontSize: 16 },
  detail: { color: colors.textMuted, marginTop: 5 },
  status: { color: colors.primary, marginTop: 6, textTransform: 'capitalize', fontWeight: '700' },
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' },
  modal: { backgroundColor: colors.background, borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  modalTitle: { color: colors.text, fontSize: 19, fontWeight: '700' },
  close: { color: colors.primary, fontWeight: '700', padding: 8 },
  label: { color: colors.text, fontWeight: '600', marginBottom: 6, marginTop: 10 },
  input: { backgroundColor: colors.white, borderColor: colors.border, borderWidth: 1, borderRadius: 10, color: colors.text, paddingHorizontal: 12, paddingVertical: 11 },
  statuses: { flexDirection: 'row', gap: 8, marginTop: 3 },
  statusOption: { borderWidth: 1, borderColor: colors.border, borderRadius: 18, paddingHorizontal: 14, paddingVertical: 8, backgroundColor: colors.white },
  statusSelected: { borderColor: colors.primary, backgroundColor: colors.primary },
  statusText: { color: colors.text, textTransform: 'capitalize' },
  statusTextSelected: { color: colors.white },
  note: { color: colors.textMuted, marginTop: 12, fontSize: 12 },
  submit: { marginTop: 16 },
});
