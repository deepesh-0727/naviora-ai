import React from 'react';
import { Text, View } from 'react-native';
import { useCallback, useEffect, useState } from 'react';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { useRole } from '../../shared/contexts/RoleContext';

export interface StaffModuleScreenProps {
  title: string;
  endpoint: string;
}

export default function StaffModuleScreen({ title, endpoint }: StaffModuleScreenProps) {
  const { role } = useRole();
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const refresh = useCallback(async () => {
    setLoading(true); setError(false); setUnavailable(false);
    const parts = endpoint.split(' ');
    const method = parts[0]?.toUpperCase();
    const declaredPath = parts[1] ?? '';
    const path = declaredPath.replace(/^\/staff(?=\/)/, '') || '/';
    try {
      if (method !== 'GET') throw new Error(`Unsupported staff tab read method: ${method}`);
      const response = await apiClient.get<unknown>(buildApiUrl(role, path));
      setData(response.data);
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      if (status === 404 || status === 501) setUnavailable(true); else setError(true);
    } finally { setLoading(false); }
  }, [endpoint, role]);
  useEffect(() => { void refresh(); }, [refresh]);

  const rows = Array.isArray(data) ? data : typeof data === 'object' && data !== null && 'items' in data && Array.isArray(data.items) ? data.items : [];
  const scalarFields = typeof data === 'object' && data !== null && !Array.isArray(data)
    ? Object.entries(data).filter(([, value]) => value === null || ['string', 'number', 'boolean'].includes(typeof value))
    : [];

  return (
    <ScreenContainer>
      <SectionHeader title={title} />
      <View style={{ flex: 1 }}>
        {loading ? <Loader message={`Loading ${title.toLowerCase()}…`} /> : unavailable ? <BackendNotAvailable endpoint={endpoint} /> : error ? <ErrorState message={`Could not load ${title.toLowerCase()}.`} onRetry={() => void refresh()} /> : rows.length ? rows.map((row, index) => <Card key={String(typeof row === 'object' && row !== null && 'id' in row ? row.id : index)} style={{ marginBottom: 8 }}>{typeof row === 'object' && row !== null ? Object.entries(row).filter(([, value]) => value === null || ['string', 'number', 'boolean'].includes(typeof value)).map(([key, value]) => <Text key={key} style={{ paddingVertical: 3 }}>{key.split('_').join(' ')}: {value === null ? '—' : String(value)}</Text>) : <Text>{String(row)}</Text>}</Card>) : scalarFields.length ? <Card>{scalarFields.map(([key, value]) => <Text key={key} style={{ paddingVertical: 4 }}>{key.split('_').join(' ')}: {value === null ? '—' : String(value)}</Text>)}</Card> : <EmptyState message={`No ${title.toLowerCase()} records were returned.`} />}
      </View>
      <Text accessibilityRole="text" style={{ color: '#5F6975', textAlign: 'center' }}>
        {endpoint}
      </Text>
      {!loading ? <Button title="Retry" variant="secondary" onPress={() => void refresh()} style={{ marginTop: 10 }} /> : null}
    </ScreenContainer>
  );
}
