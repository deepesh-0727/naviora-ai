import React from 'react';
import { View } from 'react-native';
import { NavioraHeader, NavioraText, NavioraButton } from '../../components/common/AtomicComponents';

export default function DoctorAnalyticsScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: '#FAFAF7', padding: 24 }}>
      <NavioraHeader title="Analytics" subtitle="KPI overview" />
      <NavioraText type="h3" style={{ marginTop: 20 }}>Patients today</NavioraText>
      <NavioraButton label="View analytics" onPress={() => {}} style={{ marginTop: 20 }} />
    </View>
  );
}
