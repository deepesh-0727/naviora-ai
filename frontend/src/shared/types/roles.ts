export type Role =
  | 'patient'
  | 'doctor'
  | 'nurse'
  | 'front_desk'
  | 'pharmacy'
  | 'facilities'
  | 'emergency'
  | 'admin'
  | 'super_admin';

export type Zone = 'patient' | 'staff' | 'admin';

export interface AuthTokens {
  accessToken: string | null;
  refreshToken: string | null;
}

export interface RoleUser {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  role: Role;
  avatar?: string;
  blood_group?: string;
  allergies?: string[];
  emergency_contact?: string;
}

export const zoneForRole = (role: Role): Zone => {
  if (role === 'patient') return 'patient';
  if (role === 'admin' || role === 'super_admin') return 'admin';
  return 'staff';
};
