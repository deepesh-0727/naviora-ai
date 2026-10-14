import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { isAxiosError } from 'axios';
import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient } from '../../shared/services/api';

export interface AdminDataScreenProps {
  title: string;
  endpoint: string;
  description: string;
}

type Row = Record<string, unknown>;

function printable(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export default function AdminDataScreen({ title, endpoint, description }: AdminDataScreenProps) {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setUnavailable(false);
    try {
      const response = await apiClient.get<unknown>(endpoint);
      const body = response.data;
      const data = Array.isArray(body) ? body :
        typeof body === 'object' && body !== null && 'items' in body && Array.isArray(body.items) ? body.items :
        typeof body === 'object' && body !== null && 'logs' in body && Array.isArray(body.logs) ? body.logs :
        typeof body === 'object' && body !== null ? [body] : [];
      setRows(data.filter((value): value is Row => typeof value === 'object' && value !== null && !Array.isArray(value)));
    } catch (cause) {
      if (isAxiosError(cause) && (cause.response?.status === 404 || cause.response?.status === 501)) {
        setUnavailable(true);
      } else {
        setError('Could not load this administration data.');
      }
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => { void load(); }, [load]);

  return (
    <ScreenContainer>
      <SectionHeader title={title} />
      <Text style={{ color: '#65716B', marginBottom: 10 }}>{description}</Text>
      <Button title="Refresh" variant="secondary" onPress={() => void load()} />
      {loading ? <Loader message={`Loading ${title.toLowerCase()}…`} /> : unavailable ? <>
        <BackendNotAvailable endpoint={`GET ${endpoint}`} />
        <Button title="Retry" variant="secondary" onPress={() => void load()} />
      </> : error ? <ErrorState message={error} onRetry={() => void load()} /> : rows.length === 0 ? <EmptyState message={`No ${title.toLowerCase()} records are available.`} /> : (
        <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
          {rows.map((row, index) => (
            <Card key={String(row.id ?? row.key ?? index)} style={{ marginTop: 12 }}>
              {Object.entries(row).filter(([, value]) => value === null || ['string', 'number', 'boolean'].includes(typeof value)).map(([key, value]) => (
                <View key={key} style={{ paddingVertical: 5, flexDirection: 'row', gap: 10 }}>
                  <Text style={{ flex: 1, color: '#65716B', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</Text>
                  <Text selectable style={{ flex: 2, color: '#17221B', textAlign: 'right' }}>{printable(value)}</Text>
                </View>
              ))}
            </Card>
          ))}
        </ScrollView>
      )}
    </ScreenContainer>
  );
}
