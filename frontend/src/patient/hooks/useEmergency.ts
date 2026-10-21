import { useCallback, useEffect, useState } from 'react';
import { api, type EmergencyCase } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';

export type EmergencyStatus = 'idle' | 'triggering' | 'active' | 'cancelled' | 'arrived' | 'error';

export interface EmergencyState {
  emergencyCase: EmergencyCase | null;
  status: EmergencyStatus;
  error: string | null;
  backendUnavailable: boolean;
  trigger: (location: { lat: number; lng: number }, condition?: string, patientId?: string) => Promise<void>;
  cancel: () => Promise<void>;
}

export function useEmergency(): EmergencyState {
  const [emergencyCase, setEmergencyCase] = useState<EmergencyCase | null>(null);
  const [status, setStatus] = useState<EmergencyStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);

  const isUnavailable = (err: unknown): boolean => {
    const code = (err as { response?: { status?: number } }).response?.status;
    return code === 404 || code === 501;
  };

  const trigger = useCallback(async (location: { lat: number; lng: number }, condition?: string, patientId?: string) => {
    setStatus('triggering');
    setError(null);
    setBackendUnavailable(false);
    try {
      const locationText = `Lat: ${location.lat.toFixed(3)}, Lng: ${location.lng.toFixed(3)}`;
      const res = await api.patient.triggerEmergency({ location: locationText, description: condition ?? 'Emergency triggered via app' });
      setEmergencyCase(res.data);
      setStatus('active');
    } catch (err: unknown) {
      if (isUnavailable(err)) {
        setBackendUnavailable(true);
        setStatus('idle');
      } else {
        setError('Failed to trigger emergency. Please try again.');
        setStatus('error');
      }
    }
  }, []);

  const cancel = useCallback(async () => {
    if (!emergencyCase) return;
    try {
      const res = await api.patient.cancelEmergency(emergencyCase.id);
      setEmergencyCase(res.data);
      setStatus('cancelled');
    } catch {
      setError('Failed to cancel emergency.');
    }
  }, [emergencyCase]);

  useEffect(() => {
    void websocketClient.connect();

    const unsubAck = websocketClient.subscribe('emergency_ack', (payload: unknown) => {
      const p = payload as Partial<EmergencyCase>;
      setEmergencyCase((prev) => (prev ? { ...prev, ...p } : prev));
    });

    const unsubEnRoute = websocketClient.subscribe('emergency_en_route', (payload: unknown) => {
      const p = payload as Partial<EmergencyCase>;
      setEmergencyCase((prev) => (prev ? { ...prev, ...p, status: 'en_route' } : prev));
      setStatus('active');
    });

    const unsubArrived = websocketClient.subscribe('emergency_arrived', (payload: unknown) => {
      const p = payload as Partial<EmergencyCase>;
      setEmergencyCase((prev) => (prev ? { ...prev, ...p, status: 'arrived' } : prev));
      setStatus('arrived');
    });

    return () => {
      unsubAck();
      unsubEnRoute();
      unsubArrived();
    };
  }, []);

  return { emergencyCase, status, error, backendUnavailable, trigger, cancel };
}
