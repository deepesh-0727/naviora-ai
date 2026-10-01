import React from 'react';
import { View } from 'react-native';
import { NavioraHeader, NavioraText, NavioraButton } from '../../components/common/AtomicComponents';

export default function NurseDashboardScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: '#FAFAF7', padding: 24 }}>
      <NavioraHeader title="Nurse Dashboard" subtitle="Good Evening, Sarah" showBack={false} />
      <NavioraText type="h3" style={{ marginTop: 20 }}>Assigned patients</NavioraText>
      <NavioraButton label="Patient Check-in" onPress={() => {}} style={{ marginTop: 20 }} />
    </View>
  );
}
