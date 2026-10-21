import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { subscribeToAuthExpired } from '../services/auth_events';
import { getAccessToken, getRefreshToken, getRole, clearTokens, saveRole, saveTokens } from '../services/secure_store';
import type { AuthTokens, Role, RoleUser, Zone } from '../types/roles';
import { zoneForRole } from '../types/roles';

interface RoleContextValue {
  role: Role | null;
  user: RoleUser | null;
  zone: Zone | null;
  tokens: AuthTokens;
  isAuthenticated: boolean;
  login: (role: Role, tokens: AuthTokens, user: RoleUser) => Promise<void>;
  logout: () => Promise<void>;
}

const RoleContext = createContext<RoleContextValue>({
  role: null,
  user: null,
  zone: null,
  tokens: { accessToken: null, refreshToken: null },
  isAuthenticated: false,
  login: async () => undefined,
  logout: async () => undefined,
});

const decodeJwt = (token: string): Record<string, unknown> | null => {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    const pad = normalized.length % 4;
    const padded = pad ? normalized + '='.repeat(4 - pad) : normalized;
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
};

export const RoleProvider = ({ children }: { children: React.ReactNode }) => {
  const [role, setRole] = useState<Role | null>(null);
  const [user, setUser] = useState<RoleUser | null>(null);
  const [tokens, setTokens] = useState<AuthTokens>({ accessToken: null, refreshToken: null });

  useEffect(() => {
    const hydrate = async () => {
      const [storedRole, accessToken, refreshToken] = await Promise.all([
        getRole(),
        getAccessToken(),
        getRefreshToken(),
      ]);

      const resolvedRole = storedRole as Role | null;
      if (resolvedRole && accessToken) {
        const claims = decodeJwt(accessToken) ?? {};
        setRole(resolvedRole);
        setTokens({ accessToken, refreshToken });
        setUser({
          id: String(claims.sub ?? claims.user_id ?? 'local-user'),
          name: String(claims.name ?? claims.email ?? 'User'),
          email: typeof claims.email === 'string' ? claims.email : undefined,
          role: resolvedRole,
        });
      }
    };

    hydrate();
  }, []);

  useEffect(() => subscribeToAuthExpired(() => {
    setRole(null);
    setUser(null);
    setTokens({ accessToken: null, refreshToken: null });
  }), []);

  const login = async (nextRole: Role, nextTokens: AuthTokens, nextUser: RoleUser) => {
    await saveRole(nextRole);
    if (nextTokens.accessToken) {
      await saveTokens(nextTokens.accessToken, nextTokens.refreshToken ?? undefined);
    }
    setRole(nextRole);
    setTokens(nextTokens);
    setUser(nextUser);
  };

  const logout = async () => {
    await clearTokens();
    await saveRole('patient');
    setRole(null);
    setUser(null);
    setTokens({ accessToken: null, refreshToken: null });
  };

  const value = useMemo<RoleContextValue>(() => {
    const currentZone = role ? zoneForRole(role) : null;
    return {
      role,
      user,
      zone: currentZone,
      tokens,
      isAuthenticated: Boolean(role && tokens.accessToken),
      login,
      logout,
    };
  }, [role, user, tokens]);

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
};

export const useRole = () => useContext(RoleContext);
