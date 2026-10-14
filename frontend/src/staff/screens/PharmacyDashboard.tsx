import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ScrollView, Text, TextInput, View } from 'react-native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';

type Entry = Record<string, unknown>;
function rows(value: unknown): Entry[] {
  if (Array.isArray(value)) return value.filter((item): item is Entry => typeof item === 'object' && item !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) return value.items.filter((item): item is Entry => typeof item === 'object' && item !== null);
  return [];
}
function field(row: Entry, keys: string[]): string {
  for (const key of keys) { const value = row[key]; if (typeof value === 'string' || typeof value === 'number') return String(value); }
  return '—';
}

export default function PharmacyDashboard() {
  const [prescriptions, setPrescriptions] = useState<Entry[]>([]);
  const [inventory, setInventory] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [barcode, setBarcode] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true); setError(null); setUnavailable(null);
    try {
      const [prescriptionResponse, inventoryResponse] = await Promise.all([
        apiClient.get<unknown>(buildApiUrl('pharmacy', '/pharmacy/prescriptions')),
        apiClient.get<unknown>(buildApiUrl('pharmacy', '/pharmacy/inventory')),
      ]);
      setPrescriptions(rows(prescriptionResponse.data));
      setInventory(rows(inventoryResponse.data));
    } catch (reason: unknown) {
      const detail = typeof reason === 'object' && reason !== null && 'response' in reason ? reason as { response?: { status?: number }; config?: { url?: string } } : {};
      if (detail.response?.status === 404 || detail.response?.status === 501) setUnavailable(detail.config?.url ?? 'GET /staff/pharmacy/prescriptions');
      else setError('Could not load pharmacy data.');
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  const visibleInventory = useMemo(() => inventory.filter((item) => {
    const name = field(item, ['name', 'medication_name', 'barcode']).toLowerCase();
    const matchesCode = barcode.trim() === '' || name.includes(barcode.trim().toLowerCase()) || field(item, ['barcode']).toLowerCase().includes(barcode.trim().toLowerCase());
    const quantity = Number(item.quantity ?? item.stock ?? NaN);
    const threshold = Number(item.reorder_level ?? item.low_stock_threshold ?? 0);
    return matchesCode && (!lowStockOnly || (Number.isFinite(quantity) && quantity <= threshold));
  }), [barcode, inventory, lowStockOnly]);

  const perform = async (operation: 'dispense' | 'refill' | 'interaction' | 'pickup', item: Entry) => {
    const id = field(item, ['id', 'prescription_id']);
    if (id === '—') { setActionError('This prescription has no identifier and cannot be updated.'); return; }
    setBusy(id); setActionError(null); setActionMessage(null);
    const path = operation === 'dispense' ? `/pharmacy/dispense/${encodeURIComponent(id)}`
      : operation === 'refill' ? `/pharmacy/refill/${encodeURIComponent(id)}/approve`
        : operation === 'interaction' ? '/pharmacy/interaction-check' : '/pharmacy/notify-pickup';
    try {
      if (operation === 'interaction') await apiClient.post(buildApiUrl('pharmacy', path), { prescription_id: id, patient_id: item.patient_id });
      else await apiClient.post(buildApiUrl('pharmacy', path), operation === 'pickup' ? { prescription_id: id, patient_id: item.patient_id } : undefined);
      setActionMessage(operation === 'interaction' ? 'Medication interaction check completed.' : `${operation === 'pickup' ? 'Pickup notification' : operation === 'refill' ? 'Refill approval' : 'Dispensing'} submitted.`);
      await refresh();
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      setActionError(status === 404 || status === 501 ? `POST ${path} is not available on the backend yet.` : 'Pharmacy action failed. Retry when the service is available.');
    } finally { setBusy(null); }
  };

  const sortedPrescriptions = [...prescriptions].sort((a, b) => {
    const rank = (entry: Entry) => { const priority = field(entry, ['priority']).toLowerCase(); return priority === 'stat' ? 0 : priority === 'urgent' ? 1 : 2; };
    return rank(a) - rank(b);
  });

  if (loading) return <Loader message="Loading pharmacy queue…" />;
  if (unavailable) return <ScreenContainer><BackendNotAvailable endpoint={unavailable} /><Button title="Retry" variant="secondary" onPress={() => void refresh()} /></ScreenContainer>;
  if (error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  return (
    <ScreenContainer>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
        <SectionHeader title="Pharmacy" />
        {actionError ? <Card style={{ marginBottom: 10 }}><Text style={{ color: '#B42318' }}>{actionError}</Text><Button title="Dismiss" variant="secondary" onPress={() => setActionError(null)} /></Card> : null}
        {actionMessage ? <Text style={{ color: '#1D8A6C', marginBottom: 10 }}>{actionMessage}</Text> : null}
        <Card style={{ marginBottom: 12 }}><Text style={{ fontWeight: '700', fontSize: 17, marginBottom: 8 }}>Prescription queue</Text>
          {sortedPrescriptions.length === 0 ? <EmptyState message="No prescriptions are waiting for pharmacy review." /> : sortedPrescriptions.map((item, index) => {
            const id = field(item, ['id', 'prescription_id']);
            return <Card key={`${id}-${index}`} style={{ marginBottom: 8 }}><Text style={{ fontWeight: '700' }}>{field(item, ['medication_name', 'drug_name', 'name'])} · {field(item, ['priority'])}</Text><Text style={{ marginVertical: 6 }}>Patient {field(item, ['patient_id'])} · Qty {field(item, ['quantity'])} · {field(item, ['status'])}</Text><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}><Button title="Check interactions" variant="secondary" disabled={busy === id} onPress={() => void perform('interaction', item)} /><Button title="Dispense" disabled={busy === id} onPress={() => void perform('dispense', item)} /><Button title="Approve refill" variant="secondary" disabled={busy === id} onPress={() => void perform('refill', item)} /><Button title="Notify pickup" variant="secondary" disabled={busy === id} onPress={() => void perform('pickup', item)} /></View></Card>;
          })}
        </Card>
        <Card><Text style={{ fontWeight: '700', fontSize: 17, marginBottom: 8 }}>Inventory</Text>
          <TextInput value={barcode} onChangeText={setBarcode} placeholder="Search name or enter barcode" style={{ borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 10, marginBottom: 8 }} />
          <Button title={lowStockOnly ? 'Show all stock' : 'Filter low stock'} variant="secondary" onPress={() => setLowStockOnly((current) => !current)} />
          {visibleInventory.length === 0 ? <EmptyState message="No inventory items match this filter." /> : visibleInventory.map((item, index) => <Text key={field(item, ['id', 'barcode']) + index} style={{ paddingVertical: 8 }}>{field(item, ['name', 'medication_name'])} · Stock {field(item, ['quantity', 'stock'])} · Reorder at {field(item, ['reorder_level', 'low_stock_threshold'])}</Text>)}
        </Card>
        <Button title="Refresh pharmacy data" variant="secondary" onPress={() => void refresh()} style={{ marginTop: 12 }} />
      </ScrollView>
    </ScreenContainer>
  );
}
