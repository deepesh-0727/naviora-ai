import React, { createContext, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiService } from '../services/api';

export type UserRole = 'patient' | 'doctor' | 'nurse' | 'staff' | 'admin';

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
  loginWithCredentials: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
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

  const loginWithCredentials = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    // Use OAuth2 form-encoded login (FastAPI standard)
    const result = await apiService.postForm<{ access_token: string; refresh_token: string; token_type: string }>(
      '/auth/login',
      { username: email.trim().toLowerCase(), password }
    );

    if (!result.data?.access_token) {
      return { success: false, error: result.error || 'Invalid email or password.' };
    }

    // Store tokens
    await AsyncStorage.setItem('access_token', result.data.access_token);
    if (result.data.refresh_token) {
      await AsyncStorage.setItem('refresh_token', result.data.refresh_token);
    }

    const meRes = await apiService.get<any>('/auth/me');
    const profileRes = meRes.data ? { data: undefined } : await apiService.get<any>('/patients/profile');

    const userData = meRes.data || profileRes.data;
    if (!userData) {
      return { success: false, error: 'Failed to load user profile.' };
    }

    const authUser: AuthUser = {
      id: String(userData.id || userData.user_id),
      name: userData.full_name || userData.name || `${userData.first_name || ''} ${userData.last_name || ''}`.trim() || email,
      email: userData.email || email,
      role: normalizeRole(userData.role),
      phone: userData.phone,
      avatar: userData.avatar_url,
      token: result.data.access_token,
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

function normalizeRole(role: unknown): UserRole {
  if (role === 'doctor' || role === 'nurse' || role === 'staff' || role === 'admin') {
    return role;
  }
  return 'patient';
}

export const useAuth = () => useContext(AuthContext);
