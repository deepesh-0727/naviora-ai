import * as SecureStore from 'expo-secure-store';

const keys = {
  accessToken: 'access_token',
  refreshToken: 'refresh_token',
  role: 'selected_role',
};

export const normalizeStoredToken = (value: string): string =>
  value.trim().replace(/^Bearer\s+/i, '').replace(/^['"]|['"]$/g, '').trim();

export const saveTokens = async (accessToken: string, refreshToken?: string): Promise<void> => {
  await SecureStore.setItemAsync(keys.accessToken, normalizeStoredToken(accessToken));
  if (refreshToken) {
    await SecureStore.setItemAsync(keys.refreshToken, normalizeStoredToken(refreshToken));
  }
};

export const getAccessToken = async (): Promise<string | null> =>
  SecureStore.getItemAsync(keys.accessToken);

export const saveAccessToken = async (accessToken: string): Promise<void> =>
  SecureStore.setItemAsync(keys.accessToken, normalizeStoredToken(accessToken));

export const getRefreshToken = async (): Promise<string | null> =>
  SecureStore.getItemAsync(keys.refreshToken);

export const clearTokens = async (): Promise<void> => {
  await SecureStore.deleteItemAsync(keys.accessToken);
  await SecureStore.deleteItemAsync(keys.refreshToken);
};

export const saveRole = async (role: string): Promise<void> => {
  await SecureStore.setItemAsync(keys.role, role);
};

export const getRole = async (): Promise<string | null> => SecureStore.getItemAsync(keys.role);
