import { useCallback, useEffect, useState } from 'react';
import { api, type Appointment } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';

export interface QueueState {
  appointments: Appointment[];
  loading: boolean;
  error: string | null;
  backendUnavailable: boolean;
  refresh: () => void;
}

export function useQueue(): QueueState {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBackendUnavailable(false);
    try {
      const res = await api.patient.getAppointments({ upcoming: true });
      setAppointments(Array.isArray(res.data) ? res.data : []);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status === 404 || status === 501) {
        setBackendUnavailable(true);
      } else {
        setError('Failed to load queue. Please retry.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchQueue();
    void websocketClient.connect();

    const unsubQueue = websocketClient.subscribe('queue_update', () => {
      void fetchQueue();
    });
    const unsubAppt = websocketClient.subscribe('appointment_update', () => {
      void fetchQueue();
    });

    return () => {
      unsubQueue();
      unsubAppt();
    };
  }, [fetchQueue]);

  return { appointments, loading, error, backendUnavailable, refresh: fetchQueue };
}
