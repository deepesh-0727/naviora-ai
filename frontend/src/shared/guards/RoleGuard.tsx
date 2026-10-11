import React from 'react';
import { View, Text } from 'react-native';

import { useRole } from '../contexts/RoleContext';
import type { Role } from '../types/roles';

interface RoleGuardProps {
  allow: Role[];
  children: React.ReactNode;
}

export const RoleGuard = ({ allow, children }: RoleGuardProps) => {
  const { role } = useRole();

  if (!role || !allow.includes(role)) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <Text>Unauthorized</Text>
      </View>
    );
  }

  return <>{children}</>;
};

export default RoleGuard;
