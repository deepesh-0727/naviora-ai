import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet } from 'react-native';
import { NavioraCard, NavioraHeader, NavioraText } from '../components/common/AtomicComponents';
import { useTheme } from '../context/ThemeContext';
import { apiService } from '../services/api';
export default function BillingScreen() {
  const theme = useTheme(); const [invoices, setInvoices] = useState<any[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const load = useCallback(async () => { setLoading(true); const r = await apiService.get<any>('/billing/invoices'); const rows = Array.isArray(r.data) ? r.data : r.data?.invoices || []; setInvoices(rows); setError(r.error || ''); setLoading(false); }, []);
  useEffect(() => { void load(); }, [load]);
  return <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}><ScrollView contentContainerStyle={styles.content}><NavioraHeader title="Billing & Payments" subtitle="Medical charges and insurance" />
    {loading ? <ActivityIndicator color={theme.colors.primary} /> : error ? <NavioraText color="danger">{error}</NavioraText> : invoices.length === 0 ? <NavioraText color="secondary">No invoices are available.</NavioraText> : invoices.map((invoice, i) => <NavioraCard key={String(invoice.id || i)} style={styles.card}><NavioraText type="body" style={{ fontWeight: '700' }}>{invoice.invoice_number || invoice.number || 'Invoice'}</NavioraText><NavioraText type="h3" style={{ marginTop: 8 }}>{invoice.amount ?? '—'}</NavioraText><NavioraText type="caption" color="secondary">{invoice.status || 'Status unavailable'}{invoice.created_at ? ` • ${new Date(invoice.created_at).toLocaleDateString()}` : ''}</NavioraText></NavioraCard>)}
  </ScrollView></SafeAreaView>;
}
const styles = StyleSheet.create({ screen: { flex: 1 }, content: { padding: 20 }, card: { marginBottom: 12 } });
