import { useCallback, useEffect, useState } from 'react';

import { apiClient, buildApiUrl } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';

export type WardBed = Record<string, unknown>;

function toBeds(value: unknown): WardBed[] {
  if (Array.isArray(value)) return value.filter((item): item is WardBed => typeof item === 'object' && item !== null);
  if (typeof value === 'object' && value !== null && 'beds' in value && Array.isArray(value.beds)) {
    return value.beds.filter((item): item is WardBed => typeof item === 'object' && item !== null);
  }
  return [];
}

export function useWardState(wardId: string | number | null | undefined) {
  const [beds, setBeds] = useState<WardBed[]>([]);
  const [loading, setLoading] = useState(Boolean(wardId));
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);

  const refresh = useCallback(async () => {
    if (wardId === null || wardId === undefined || String(wardId).trim() === '') {
      setBeds([]);
      setLoading(false);
      setError('Select a ward to view bed status.');
      return;
    }
    setLoading(true);
    setError(null);
    setBackendUnavailable(false);
    try {
      const response = await apiClient.get<unknown>(buildApiUrl('nurse', `/nurse/ward/${encodeURIComponent(String(wardId))}/beds`));
      setBeds(toBeds(response.data));
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason
        ? (reason as { response?: { status?: number } }).response?.status
        : undefined;
      setBackendUnavailable(status === 404 || status === 501);
      setError(status === 404 || status === 501 ? null : 'Could not load ward bed status.');
    } finally {
      setLoading(false);
    }
  }, [wardId]);

  useEffect(() => {
    void refresh();
    void websocketClient.connect();
    const unsubscribe = websocketClient.subscribe('ward_update', () => { void refresh(); });
    return unsubscribe;
  }, [refresh]);

  return { beds, loading, error, backendUnavailable, empty: !loading && !error && !backendUnavailable && beds.length === 0, refresh };
}
