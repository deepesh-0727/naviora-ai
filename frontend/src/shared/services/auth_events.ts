import AsyncStorage from '@react-native-async-storage/async-storage';
import { clearTokens } from './secure_store';

type AuthExpiredListener = () => void;
const authExpiredListeners = new Set<AuthExpiredListener>();
let clearSessionInFlight: Promise<void> | null = null;

export const subscribeToAuthExpired = (listener: AuthExpiredListener): (() => void) => {
  authExpiredListeners.add(listener);
  return () => authExpiredListeners.delete(listener);
};

export const expireAuthSession = async (): Promise<void> => {
  if (clearSessionInFlight) return clearSessionInFlight;

  clearSessionInFlight = (async () => {
    await Promise.allSettled([
      AsyncStorage.multiRemove(['auth_user', 'access_token', 'refresh_token']),
      clearTokens(),
    ]);
    console.log('401 UNAUTHORIZED: Tokens cleared. Logging out.');
    authExpiredListeners.forEach((listener) => listener());
  })();

  try {
    await clearSessionInFlight;
  } finally {
    clearSessionInFlight = null;
  }
};
