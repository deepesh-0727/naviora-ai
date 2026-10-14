import React, { useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth } from '../context/AuthContext';
import PatientNavigator from '../patient/navigator/PatientNavigator';
import RoleBasedNavigator from './RoleBasedNavigator';
import StaffNavigator from '../staff/navigator/StaffNavigator';
import { useRole } from '../shared/contexts/RoleContext';
import type { Role } from '../shared/types/roles';

const STAFF_ROLES: Role[] = ['doctor', 'nurse', 'front_desk', 'pharmacy', 'facilities', 'emergency'];
const CONTEXT_ROLES: Role[] = [...STAFF_ROLES, 'admin', 'super_admin'];

/** Keep the signed-in role synchronized with the shared API/session context. */
export default function PatientRoleNavigator() {
  const { user } = useAuth();
  const { role, login } = useRole();

  useEffect(() => {
    if (!user?.token || !CONTEXT_ROLES.includes(user.role as Role) || role === user.role) return;
    let cancelled = false;
    void AsyncStorage.getItem('refresh_token').then((refreshToken) => {
      if (cancelled) return;
      return login(user.role as Role, { accessToken: user.token ?? null, refreshToken }, {
        id: user.id,
        name: user.name,
        email: user.email,
        phone: user.phone,
        avatar: user.avatar,
        role: user.role as Role,
      });
    });
    return () => { cancelled = true; };
  }, [login, role, user]);

  if (user?.role === 'patient') return <PatientNavigator />;
  if (user && STAFF_ROLES.includes(user.role as Role)) return <StaffNavigator />;
  return <RoleBasedNavigator />;
}
