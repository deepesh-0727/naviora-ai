import { useCallback, useEffect, useState } from 'react';
import {
  api,
  type Appointment,
  type Department,
  type Doctor,
} from '../../shared/services/api';

export interface AppointmentsState {
  upcoming: Appointment[];
  past: Appointment[];
  departments: Department[];
  doctors: Doctor[];
  availability: string[];
  loading: boolean;
  error: string | null;
  backendUnavailable: boolean;
  refresh: () => void;
  fetchDoctors: (departmentId?: number) => Promise<void>;
  fetchAvailability: (doctorId: number) => Promise<void>;
  book: (payload: {
    doctor_id: number;
    department_id: number;
    scheduled_time: string;
    symptoms?: string;
  }) => Promise<Appointment | null>;
  cancel: (id: number) => Promise<boolean>;
  reschedule: (id: number, scheduledTime: string) => Promise<boolean>;
}

export function useAppointments(): AppointmentsState {
  const [upcoming, setUpcoming] = useState<Appointment[]>([]);
  const [past, setPast] = useState<Appointment[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [availability, setAvailability] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);

  const isUnavailable = (err: unknown): boolean => {
    const status = (err as { response?: { status?: number } }).response?.status;
    return status === 404 || status === 501;
  };

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBackendUnavailable(false);
    try {
      const [apptRes, deptRes] = await Promise.all([
        api.patient.getAppointments(),
        api.patient.getDepartments(),
      ]);

      const all = Array.isArray(apptRes.data) ? apptRes.data : [];
      const now = new Date().toISOString();
      setUpcoming(all.filter((a) => a.scheduled_time >= now));
      setPast(all.filter((a) => a.scheduled_time < now));
      setDepartments(Array.isArray(deptRes.data) ? deptRes.data : []);
    } catch (err: unknown) {
      if (isUnavailable(err)) {
        setBackendUnavailable(true);
      } else {
        setError('Failed to load appointments. Please retry.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDoctors = useCallback(async (departmentId?: number) => {
    try {
      const params = departmentId ? { department_id: departmentId } : undefined;
      const res = await api.patient.getDoctors(params);
      setDoctors(Array.isArray(res.data) ? res.data : []);
    } catch {
      setDoctors([]);
    }
  }, []);

  const fetchAvailability = useCallback(async (doctorId: number) => {
    try {
      const res = await api.patient.getAppointmentAvailability(doctorId);
      setAvailability(res.data?.available_slots ?? []);
    } catch {
      setAvailability([]);
    }
  }, []);

  const book = useCallback(
    async (payload: {
      doctor_id: number;
      department_id: number;
      scheduled_time: string;
      symptoms?: string;
    }): Promise<Appointment | null> => {
      try {
        const res = await api.patient.createAppointment(payload);
        await fetchAll();
        return res.data;
      } catch {
        return null;
      }
    },
    [fetchAll],
  );

  const cancel = useCallback(
    async (id: number): Promise<boolean> => {
      try {
        await api.patient.cancelAppointment(id);
        await fetchAll();
        return true;
      } catch {
        return false;
      }
    },
    [fetchAll],
  );

  const reschedule = useCallback(
    async (id: number, scheduledTime: string): Promise<boolean> => {
      try {
        await api.patient.rescheduleAppointment(id, scheduledTime);
        await fetchAll();
        return true;
      } catch {
        return false;
      }
    },
    [fetchAll],
  );

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  return {
    upcoming,
    past,
    departments,
    doctors,
    availability,
    loading,
    error,
    backendUnavailable,
    refresh: fetchAll,
    fetchDoctors,
    fetchAvailability,
    book,
    cancel,
    reschedule,
  };
}
