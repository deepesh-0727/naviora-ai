import React from 'react';
import { useAuth } from '../context/AuthContext';
import PatientNavigator from '../patient/navigator/PatientNavigator';
import RoleBasedNavigator from './RoleBasedNavigator';

/** Mount the patient-zone navigator for patients; preserve the existing staff/admin navigator. */
export default function PatientRoleNavigator() {
  const { user } = useAuth();
  return user?.role === 'patient' ? <PatientNavigator /> : <RoleBasedNavigator />;
}
