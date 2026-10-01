import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import { NavioraBadge, NavioraCard, NavioraHeader, NavioraText } from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { apiService } from '../../services/api';
export default function InventoryScreen() {
  const theme = useTheme(); const [items, setItems] = useState<any[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const load = useCallback(async () => { setLoading(true); const r = await apiService.get<any>('/pharmacy/inventory'); const rows = Array.isArray(r.data) ? r.data : r.data?.items || []; setItems(rows); setError(r.error || ''); setLoading(false); }, []);
  useEffect(() => { void load(); }, [load]);
  return <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}><ScrollView contentContainerStyle={styles.content}><NavioraHeader title="Inventory Management" subtitle="Pharmacy and supply levels" />
    {loading ? <ActivityIndicator color={theme.colors.primary} /> : error ? <NavioraText color="danger">{error}</NavioraText> : items.length === 0 ? <NavioraText color="secondary">No inventory items are available.</NavioraText> : items.map((item, i) => <NavioraCard key={String(item.id || i)} style={styles.card}><View style={styles.row}><View style={{ flex: 1 }}><NavioraText type="body" style={{ fontWeight: '700' }}>{item.name || item.item || 'Inventory item'}</NavioraText><NavioraText type="caption" color="secondary">Quantity: {item.quantity ?? item.qty ?? '—'}</NavioraText></View><NavioraBadge label={item.status || 'Available'} tone="info" /></View></NavioraCard>)}
  </ScrollView></SafeAreaView>;
}
const styles = StyleSheet.create({ screen: { flex: 1 }, content: { padding: 20 }, card: { marginTop: 12 }, row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' } });
