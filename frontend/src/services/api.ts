import AsyncStorage from '@react-native-async-storage/async-storage';
import { CONFIG } from '../../config';
const BASE_URL = 'https://naviora-backend-s6je.onrender.com/api/v1';

export interface APIResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

async function request<T>(
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' = 'GET',
  body?: any
): Promise<APIResponse<T>> {
  const url = `${BASE_URL}${endpoint}`;
  const token = await AsyncStorage.getItem('access_token');
  const language = await AsyncStorage.getItem('language');
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'Accept-Language': language || 'en',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    const status = response.status;
    let data;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.ok) {
      return { data, status };
    } else {
      return {
        error: data?.detail || 'An error occurred while calling the service',
        status,
      };
    }
  } catch (err: any) {
    return {
      error: err.message || 'Network connectivity issue. Please check your network connection.',
      status: 0,
    };
  }
}

async function requestForm<T>(endpoint: string, body: Record<string, string>): Promise<APIResponse<T>> {
  const token = await AsyncStorage.getItem('access_token');
  try {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: new URLSearchParams(body).toString(),
    });
    const data = await response.json().catch(() => null);
    return response.ok ? { data, status: response.status } : { error: data?.detail || 'Request failed', status: response.status };
  } catch (error: any) {
    return { error: error.message || 'Network connectivity issue', status: 0 };
  }
}

export const apiService = {
  get: <T>(endpoint: string) => request<T>(endpoint, 'GET'),
  post: <T>(endpoint: string, body: any) => request<T>(endpoint, 'POST', body),
  put: <T>(endpoint: string, body: any) => request<T>(endpoint, 'PUT', body),
  delete: <T>(endpoint: string) => request<T>(endpoint, 'DELETE'),
  patch: <T>(endpoint: string, body: any) => request<T>(endpoint, 'PATCH', body),
  postForm: <T>(endpoint: string, body: Record<string, string>) => requestForm<T>(endpoint, body),
};
