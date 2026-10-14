import { useCallback, useEffect, useState } from 'react';

import { apiClient, buildApiUrl } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';

export type DoctorQueueEntry = Record<string, unknown>;

interface QueuePayload {
  items?: DoctorQueueEntry[];
  results?: DoctorQueueEntry[];
}

export function useDoctorQueue() {
  const [queue, setQueue] = useState<DoctorQueueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBackendUnavailable(false);
    try {
      const response = await apiClient.get<DoctorQueueEntry[] | QueuePayload>(buildApiUrl('doctor', '/doctor/queue'));
      const payload = response.data;
      setQueue(Array.isArray(payload) ? payload : payload.items ?? payload.results ?? []);
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason
        ? (reason as { response?: { status?: number } }).response?.status
        : undefined;
      setBackendUnavailable(status === 404 || status === 501);
      setError(status === 404 || status === 501 ? null : 'Could not load the doctor queue.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    void websocketClient.connect();
    const unsubscribe = websocketClient.subscribe('queue_update', () => { void refresh(); });
    return unsubscribe;
  }, [refresh]);

  return { queue, loading, error, backendUnavailable, empty: !loading && !error && !backendUnavailable && queue.length === 0, refresh };
}
