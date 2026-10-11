import * as SecureStore from 'expo-secure-store';

const keys = {
  accessToken: 'access_token',
  refreshToken: 'refresh_token',
  role: 'selected_role',
};

export const saveTokens = async (accessToken: string, refreshToken?: string): Promise<void> => {
  await SecureStore.setItemAsync(keys.accessToken, accessToken);
  if (refreshToken) {
    await SecureStore.setItemAsync(keys.refreshToken, refreshToken);
  }
};

export const getAccessToken = async (): Promise<string | null> =>
  SecureStore.getItemAsync(keys.accessToken);

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
