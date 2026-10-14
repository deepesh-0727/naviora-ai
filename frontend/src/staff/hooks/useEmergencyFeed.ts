import { useCallback, useEffect, useState } from 'react';

import { apiClient, buildApiUrl } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';

export type EmergencyFeedItem = Record<string, unknown>;

function toItems(value: unknown): EmergencyFeedItem[] {
  if (Array.isArray(value)) return value.filter((item): item is EmergencyFeedItem => typeof item === 'object' && item !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) {
    return value.items.filter((item): item is EmergencyFeedItem => typeof item === 'object' && item !== null);
  }
  return [];
}

export function useEmergencyFeed() {
  const [incidents, setIncidents] = useState<EmergencyFeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBackendUnavailable(false);
    try {
      const response = await apiClient.get<unknown>(buildApiUrl('emergency', '/emergency/active'));
      setIncidents(toItems(response.data));
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason
        ? (reason as { response?: { status?: number } }).response?.status
        : undefined;
      setBackendUnavailable(status === 404 || status === 501);
      setError(status === 404 || status === 501 ? null : 'Could not load active emergencies.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    void websocketClient.connect();
    const unsubscribe = websocketClient.subscribe('emergency_new', () => { void refresh(); });
    return unsubscribe;
  }, [refresh]);

  return { incidents, loading, error, backendUnavailable, empty: !loading && !error && !backendUnavailable && incidents.length === 0, refresh };
}
