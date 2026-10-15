import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios';

import { getAccessToken, getRefreshToken, saveAccessToken } from './secure_store';
import type { Role } from '../types/roles';
import { CONFIG } from '../../../config';

const API_BASE = CONFIG.API_BASE_URL.replace(/\/+$/, '').replace(/\/api\/v1$/, '');
const API_PREFIX = '/api/v1';

const buildRolePrefix = (role: Role | null): string => {
  if (role === 'patient') return '/api/v1';
  if (role === 'admin' || role === 'super_admin') return '/api/v1/admin';
  return '/api/v1/staff';
};

export const buildApiUrl = (role: Role | null, path: string) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${buildRolePrefix(role)}${normalizedPath}`;
};

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 20000,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
});

let refreshInFlight: Promise<string | null> | null = null;

apiClient.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    if (!refreshInFlight) {
      refreshInFlight = (async () => {
        const refreshToken = await getRefreshToken();
        if (!refreshToken) return null;

        try {
          const response = await axios.post(`${API_BASE}${API_PREFIX}/auth/refresh`, { refresh_token: refreshToken });
          const accessToken = response.data?.access_token ?? response.data?.token;
          if (typeof accessToken !== 'string' || accessToken.length === 0) return null;
          await saveAccessToken(accessToken);
          return accessToken;
        } catch {
          return null;
        }
      })().finally(() => {
        refreshInFlight = null;
      });
    }

    const token = await refreshInFlight;
    if (!token) {
      return Promise.reject(error);
    }

    const headers = originalRequest.headers ?? {};
    headers.Authorization = `Bearer ${token}`;
    originalRequest.headers = headers;
    return apiClient(originalRequest);
  }
);

export type ApiResult<T> = AxiosResponse<T>;

export interface Appointment {
  id: number;
  doctor_name: string;
  department_name: string;
  scheduled_time: string;
  status: string;
  queue_position: number;
  estimated_wait_minutes: number;
}

export interface Department {
  id: number;
  name: string;
  description?: string | null;
}

export interface Doctor {
  id: number;
  first_name?: string;
  last_name?: string;
  name?: string;
  specialization?: string | null;
  department_id?: number | null;
}

export interface PatientProfile {
  id: number;
  first_name: string;
  last_name: string;
  email?: string | null;
  phone?: string | null;
  blood_group?: string | null;
  allergies?: string[] | null;
  emergency_contact?: string | null;
  emergency_contact_name?: string | null;
  medical_history?: string | null;
  insurance_provider?: string | null;
  insurance_number?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
}

export interface PatientNotification {
  id: number;
  title?: string | null;
  message?: string | null;
  body?: string | null;
  type?: string | null;
  is_read?: boolean;
  created_at?: string | null;
}

export interface EmergencyCase {
  id: number;
  status: string;
  priority?: string;
  location?: string;
  assigned_staff?: Record<string, unknown> | null;
  arrival_time?: string | null;
}

export const api = {
  auth: {
    login: <T = unknown>(payload: Record<string, unknown>) => apiClient.post<T>(`${API_BASE}${API_PREFIX}/auth/login`, payload),
    otpVerify: <T = unknown>(role: Role | null, payload: Record<string, unknown>) =>
      apiClient.post<T>(buildApiUrl(role, '/auth/otp/verify'), payload),
    refresh: <T = unknown>(payload: Record<string, unknown>) => apiClient.post<T>(`${API_BASE}${API_PREFIX}/auth/refresh`, payload),
  },
  patient: {
    getProfile: () => apiClient.get<PatientProfile>(buildApiUrl('patient', '/patients/profile')),
    updateProfile: (payload: Partial<PatientProfile>) =>
      apiClient.put<PatientProfile>(buildApiUrl('patient', '/patients/profile'), payload),
    getAppointments: (params?: Record<string, string | boolean | number>) =>
      apiClient.get<Appointment[]>(buildApiUrl('patient', '/appointments'), { params }),
    createAppointment: (payload: {
      doctor_id: number;
      department_id: number;
      scheduled_time: string;
      symptoms?: string;
    }) => apiClient.post<Appointment>(buildApiUrl('patient', '/appointments'), payload),
    getAppointmentAvailability: (doctorId: number) =>
      apiClient.get<{ available_slots: string[]; is_available: boolean }>(
        buildApiUrl('patient', `/appointments/doctor/${doctorId}/availability`)
      ),
    cancelAppointment: (id: number) =>
      apiClient.delete<void>(buildApiUrl('patient', `/appointments/${id}`)),
    rescheduleAppointment: (id: number, scheduledTime: string) =>
      apiClient.put<Appointment>(buildApiUrl('patient', `/appointments/${id}`), { scheduled_time: scheduledTime }),
    getDepartments: () => apiClient.get<Department[]>(buildApiUrl('patient', '/navigation/departments')),
    getDoctors: (params?: Record<string, string | number>) =>
      apiClient.get<Doctor[]>(buildApiUrl('patient', '/doctors'), { params }),
    getNotifications: (params?: Record<string, string | boolean | number>) =>
      apiClient.get<PatientNotification[]>(buildApiUrl('patient', '/notifications'), { params }),
    markNotificationRead: (id: number) =>
      apiClient.put<{ message: string }>(buildApiUrl('patient', `/notifications/${id}/read`)),
    deleteNotification: (id: number) =>
      apiClient.delete<{ message: string }>(buildApiUrl('patient', `/notifications/${id}`)),
    triggerEmergency: (payload: { location: { lat: number; lng: number }; patient_id?: string; condition?: string }) =>
      apiClient.post<EmergencyCase>(buildApiUrl('patient', '/emergency/trigger'), payload),
    cancelEmergency: (id: number) =>
      apiClient.post<EmergencyCase>(buildApiUrl('patient', `/emergency/${id}/cancel`)),
    getEmergencyStatus: (id: number) =>
      apiClient.get<EmergencyCase>(buildApiUrl('patient', `/emergency/status/${id}`)),
    getNavigationDepartments: () => apiClient.get<Department[]>(buildApiUrl('patient', '/navigation/departments')),
    getNavigationRoute: (startNode: string, endNode: string, accessible = false) =>
      apiClient.get<{ steps?: Array<string | { instruction?: string; text?: string; description?: string }>; directions?: Array<string | { instruction?: string; text?: string; description?: string }> }>(buildApiUrl('patient', '/navigation/route'), {
        params: { from: startNode, to: endNode, accessible },
      }),
    getNavigationAmenities: () =>
      apiClient.get<{ pois?: Array<{ name: string; location: string }> }>(buildApiUrl('patient', '/navigation/amenities'), { params: { type: 'restroom' } }),
    processVoice: (form: FormData) =>
      apiClient.post<{
        text?: string;
        intent?: string;
        entities?: Record<string, unknown>;
        response_text?: string;
        response_audio_url?: string | null;
        fallback_used?: boolean;
        fallback_reason?: string | null;
      }>(
        buildApiUrl('patient', '/voice/process'),
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      ),
    getSettings: () => apiClient.get<Record<string, unknown>>(buildApiUrl('patient', '/settings')),
    updateSettings: (payload: Record<string, unknown>) =>
      apiClient.put<Record<string, unknown>>(buildApiUrl('patient', '/settings'), payload),
    deleteAccount: (password: string) => apiClient.delete<void>(buildApiUrl('patient', '/auth/account'), { data: { password } }),
  },
  staff: {
    getQueue: <T = unknown>() => apiClient.get<T>(buildApiUrl('doctor', '/staff/doctor/queue')),
    getDoctorSchedule: <T = unknown>(date?: string) =>
      apiClient.get<T>(buildApiUrl('doctor', '/staff/doctor/schedule'), { params: { date } }),
  },
  admin: {
    getDashboard: <T = unknown>() => apiClient.get<T>(buildApiUrl('admin', '/admin/dashboard/kpis')),
    getUsers: <T = unknown>() => apiClient.get<T>(buildApiUrl('admin', '/admin/users')),
  },
};

export default apiClient;
