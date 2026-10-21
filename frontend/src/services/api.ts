import AsyncStorage from '@react-native-async-storage/async-storage';
import { CONFIG } from '../../config';
import { expireAuthSession } from '../shared/services/auth_events';

export interface APIResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function getErrorMessage(data: unknown, fallback: string): string {
  if (!isRecord(data)) {
    return fallback;
  }

  const nestedError = isRecord(data.error) ? data.error : undefined;
  const message = [
    data.detail,
    nestedError?.message,
    typeof data.error === 'string' ? data.error : undefined,
    data.message,
  ].find((candidate): candidate is string => typeof candidate === 'string' && candidate.trim().length > 0);

  const details = nestedError?.details ?? data.details;
  if (Array.isArray(details)) {
    const detailMessages = details.flatMap(detail => {
      if (!isRecord(detail) || typeof detail.msg !== 'string') {
        return [];
      }
      const location = Array.isArray(detail.loc)
        ? detail.loc
            .filter((part): part is string | number => typeof part === 'string' || typeof part === 'number')
            .filter(part => part !== 'body')
            .join('.')
        : '';
      return [location ? `${location}: ${detail.msg}` : detail.msg];
    });
    if (detailMessages.length > 0) {
      return message
        ? `${message}: ${detailMessages.join(' ')}`
        : detailMessages.join(' ');
    }
  }

  return message || fallback;
}

async function request<T>(
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' = 'GET',
  body?: any
): Promise<APIResponse<T>> {
  const url = `${CONFIG.API_BASE_URL}${endpoint}`;
  const token = await AsyncStorage.getItem('access_token');
  const language = await AsyncStorage.getItem('language');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'Accept-Language': language || 'en',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  console.log('API REQUEST:', method, url);
  console.log('HEADERS:', {
    'Content-Type': headers['Content-Type'],
    'Accept-Language': headers['Accept-Language'],
    Authorization: token ? '[REDACTED; present]' : '[not present]',
  });

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
      console.log('API ERROR:', `${method} ${url} returned HTTP ${status}`);
      console.log('API ERROR DATA:', data);
      if (status === 401 && token) await expireAuthSession();
      return {
        error: getErrorMessage(data, 'An error occurred while calling the service'),
        status,
      };
    }
  } catch (err: any) {
    console.log('API ERROR:', err?.message || 'Unknown fetch error');
    return {
      error: err.message || 'Network connectivity issue. Please check your network connection.',
      status: 0,
    };
  }
}

async function requestForm<T>(endpoint: string, body: Record<string, string>): Promise<APIResponse<T>> {
  const token = await AsyncStorage.getItem('access_token');
  try {
    const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: new URLSearchParams(body).toString(),
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 && token) await expireAuthSession();
    return response.ok
      ? { data, status: response.status }
      : { error: getErrorMessage(data, 'Request failed'), status: response.status };
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
