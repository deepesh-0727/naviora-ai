import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios';

import { getAccessToken, getRefreshToken } from './secure_store';
import type { Role } from '../types/roles';

const API_BASE = (process.env.EXPO_PUBLIC_API_URL ?? 'https://example.invalid').replace(/\/+$/, '');

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
          const response = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken });
          const accessToken = response.data?.access_token ?? response.data?.token;
          if (!accessToken) return null;
          return accessToken;
        } catch {
          return null;
        }
      })();
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

export const api = {
  auth: {
    login: <T = unknown>(payload: Record<string, unknown>) => apiClient.post<T>(`${API_BASE}/auth/login`, payload),
    otpVerify: <T = unknown>(role: Role | null, payload: Record<string, unknown>) =>
      apiClient.post<T>(buildApiUrl(role, '/auth/otp/verify'), payload),
    refresh: <T = unknown>(payload: Record<string, unknown>) => apiClient.post<T>(`${API_BASE}/auth/refresh`, payload),
  },
  patient: {
    getProfile: <T = unknown>() => apiClient.get<T>(buildApiUrl('patient', '/patients/profile')),
    updateProfile: <T = unknown>(payload: Record<string, unknown>) =>
      apiClient.put<T>(buildApiUrl('patient', '/patients/profile'), payload),
    getAppointments: <T = unknown>(params?: Record<string, unknown>) =>
      apiClient.get<T>(buildApiUrl('patient', '/appointments'), { params }),
    getNotifications: <T = unknown>(params?: Record<string, unknown>) =>
      apiClient.get<T>(buildApiUrl('patient', '/notifications'), { params }),
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
