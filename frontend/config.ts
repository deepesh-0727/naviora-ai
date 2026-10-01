import Constants from 'expo-constants';
import { Platform } from 'react-native';

const ENV = process.env.EXPO_PUBLIC_ENV || process.env.NODE_ENV || 'development';

const ENV_URLS: Record<string, string> = {
  development: 'http://localhost:8000',
  staging: 'https://naviora-staging.onrender.com',
  production: 'https://naviora-backend.onrender.com',
};

const getHostUrl = (): string => {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  
  if (ENV === 'production' || ENV === 'staging') {
    return ENV_URLS[ENV];
  }

  const debuggerHost = Constants.manifest?.debuggerHost || Constants.manifest2?.extra?.expoGo?.debuggerHost;
  if (debuggerHost) {
    const ip = debuggerHost.split(':')[0];
    return `http://${ip}:8000`;
  }
  
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000';
  }
  
  return 'http://localhost:8000';
};

const rawHost = getHostUrl();
const BASE = rawHost.endsWith('/api/v1') ? rawHost.slice(0, -7) : rawHost;

export const CONFIG = {
  API_BASE_URL: rawHost.endsWith('/api/v1') ? rawHost : `${BASE}/api/v1`,
  WS_BASE_URL: process.env.EXPO_PUBLIC_WS_URL || `${BASE.replace(/^http/, 'ws')}/ws`,
  ENVIRONMENT: ENV,
};

export default CONFIG;
