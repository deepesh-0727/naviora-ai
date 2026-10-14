import { useCallback, useEffect, useState } from 'react';

import { apiClient, buildApiUrl } from '../../shared/services/api';

export type PatientRecordSection = Record<string, unknown>;
export interface PatientRecordBundle {
  patient: PatientRecordSection | null;
  history: PatientRecordSection[];
  vitals: PatientRecordSection[];
  labs: PatientRecordSection[];
  prescriptions: PatientRecordSection[];
}

const emptyRecord: PatientRecordBundle = { patient: null, history: [], vitals: [], labs: [], prescriptions: [] };

function listFrom(value: unknown): PatientRecordSection[] {
  if (Array.isArray(value)) return value.filter((item): item is PatientRecordSection => typeof item === 'object' && item !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) {
    return value.items.filter((item): item is PatientRecordSection => typeof item === 'object' && item !== null);
  }
  return [];
}

export function usePatientRecord(patientId: string | number | null | undefined) {
  const [record, setRecord] = useState<PatientRecordBundle>(emptyRecord);
  const [loading, setLoading] = useState(Boolean(patientId));
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);

  const refresh = useCallback(async () => {
    if (patientId === null || patientId === undefined || String(patientId).trim() === '') {
      setRecord(emptyRecord);
      setLoading(false);
      setError('Select a patient to view their record.');
      return;
    }
    setLoading(true);
    setError(null);
    setBackendUnavailable(false);
    const base = `/patients/${encodeURIComponent(String(patientId))}`;
    try {
      const responses = await Promise.all([
        apiClient.get<unknown>(buildApiUrl('doctor', base)),
        apiClient.get<unknown>(buildApiUrl('doctor', `${base}/history`)),
        apiClient.get<unknown>(buildApiUrl('doctor', `${base}/vitals`)),
        apiClient.get<unknown>(buildApiUrl('doctor', `${base}/labs`)),
        apiClient.get<unknown>(buildApiUrl('doctor', `${base}/prescriptions`)),
      ]);
      const patient = responses[0].data;
      setRecord({
        patient: typeof patient === 'object' && patient !== null ? patient as PatientRecordSection : null,
        history: listFrom(responses[1].data),
        vitals: listFrom(responses[2].data),
        labs: listFrom(responses[3].data),
        prescriptions: listFrom(responses[4].data),
      });
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason
        ? (reason as { response?: { status?: number } }).response?.status
        : undefined;
      setBackendUnavailable(status === 404 || status === 501);
      setError(status === 404 || status === 501 ? null : 'Could not load this patient record.');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => { void refresh(); }, [refresh]);

  return { record, loading, error, backendUnavailable, empty: !loading && !error && !backendUnavailable && record.patient === null, refresh };
}
