import React, { createContext, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiService } from '../services/api';
import { clearTokens, normalizeStoredToken, saveTokens } from '../shared/services/secure_store';

export type UserRole = 'patient' | 'doctor' | 'nurse' | 'front_desk' | 'pharmacy' | 'facilities' | 'emergency' | 'staff' | 'admin' | 'super_admin';
export type LoginZone = 'patient' | 'staff' | 'admin';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone?: string;
  avatar?: string;
  token?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  signIn: (user: AuthUser) => Promise<void>;
  signOut: () => Promise<void>;
  updateUser: (updates: Partial<AuthUser>) => Promise<void>;
  loginWithCredentials: (identifier: string, password: string, zone?: LoginZone) => Promise<{ success: boolean; error?: string }>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  signIn: async () => {},
  signOut: async () => {},
  updateUser: async () => {},
  loginWithCredentials: async () => ({ success: false }),
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Restore session from storage
    AsyncStorage.getItem('auth_user').then((val) => {
      if (val) setUser(JSON.parse(val));
      setIsLoading(false);
    }).catch(() => setIsLoading(false));
  }, []);

  const loginWithCredentials = async (
    identifier: string,
    password: string,
    zone: LoginZone = 'patient'
  ): Promise<{ success: boolean; error?: string }> => {
    // A deliberate sign-in should never reuse tokens from an earlier account/session.
    await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
    try {
      await clearTokens();
    } catch (storageError) {
      console.log('SECURESTORE TOKEN CLEAR FAILED:', storageError instanceof Error ? storageError.message : storageError);
    }

    // Use OAuth2 form-encoded login (FastAPI standard)
    const result = await apiService.postForm<{ access_token: string; refresh_token: string; token_type: string }>(
      '/auth/login',
      { username: identifier.trim(), password }
    );

    if (!result.data?.access_token) {
      return { success: false, error: result.error || 'Incorrect email/phone number or password.' };
    }
    const accessToken = normalizeStoredToken(result.data.access_token);
    const refreshToken = result.data.refresh_token
      ? normalizeStoredToken(result.data.refresh_token)
      : undefined;

    // Keep the token available to both the shared SecureStore client and legacy
    // AsyncStorage clients. SecureStore failures must not prevent login.
    let secureStoreSaved = false;
    try {
      await saveTokens(accessToken, refreshToken);
      secureStoreSaved = true;
    } catch (storageError) {
      console.log('SECURESTORE TOKEN SAVE FAILED:', storageError instanceof Error ? storageError.message : storageError);
    }
    const tokenEntries: [string, string][] = [['access_token', accessToken]];
    if (refreshToken) {
      tokenEntries.push(['refresh_token', refreshToken]);
    }
    await AsyncStorage.multiSet(tokenEntries);
    console.log(secureStoreSaved ? 'TOKENS SAVED TO BOTH STORES' : 'TOKENS SAVED TO ASYNC STORAGE; SECURESTORE UNAVAILABLE');

    const meRes = await apiService.get<any>('/auth/me');
    const profileRes = meRes.data ? { data: undefined } : await apiService.get<any>('/patients/profile');

    const userData = meRes.data || profileRes.data;
    if (!userData) {
      await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
      await clearTokens();
      return { success: false, error: 'Failed to load user profile.' };
    }

    const role = normalizeRole(userData.role);
    const roleMatchesZone = zone === 'patient'
      ? role === 'patient'
      : zone === 'admin'
        ? role === 'admin'
        : role === 'doctor' || role === 'nurse' || role === 'front_desk' || role === 'pharmacy' || role === 'facilities' || role === 'emergency' || role === 'staff';
    if (!role || !roleMatchesZone) {
      await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
      await clearTokens();
      return {
        success: false,
        error: 'This account does not match the selected sign-in type. Choose the correct account type and try again.',
      };
    }

    const authUser: AuthUser = {
      id: String(userData.id || userData.user_id),
      name: userData.full_name || userData.name || `${userData.first_name || ''} ${userData.last_name || ''}`.trim() || identifier,
      email: userData.email || identifier,
      role,
      phone: userData.phone,
      avatar: userData.avatar_url,
      token: accessToken,
    };

    await signIn(authUser);
    return { success: true };
  };

  const signIn = async (u: AuthUser) => {
    setUser(u);
    await AsyncStorage.setItem('auth_user', JSON.stringify(u));
  };

  const signOut = async () => {
    setUser(null);
    await AsyncStorage.multiRemove(['auth_user', 'access_token', 'refresh_token']);
    await clearTokens();
  };

  const updateUser = async (updates: Partial<AuthUser>) => {
    if (!user) return;
    const updated = { ...user, ...updates };
    setUser(updated);
    await AsyncStorage.setItem('auth_user', JSON.stringify(updated));
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signOut, updateUser, loginWithCredentials }}>
      {children}
    </AuthContext.Provider>
  );
}

function normalizeRole(role: unknown): UserRole | null {
  if (role === 'doctor' || role === 'nurse' || role === 'front_desk' || role === 'pharmacy' || role === 'facilities' || role === 'emergency' || role === 'staff' || role === 'admin') {
    return role;
  }
  if (role === 'patient') return 'patient';
  return null;
}

export const useAuth = () => useContext(AuthContext);
