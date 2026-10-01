import React from 'react';
import { View } from 'react-native';
import { NavioraHeader, NavioraText, NavioraButton } from '../../components/common/AtomicComponents';

export default function DoctorScheduleScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: '#FAFAF7', padding: 24 }}>
      <NavioraHeader title="Doctor Schedule" subtitle="Appointments & availability" />
      <NavioraText type="h3" style={{ marginTop: 20 }}>Calendar overview</NavioraText>
      <NavioraButton label="Mark Available" onPress={() => {}} style={{ marginTop: 20 }} />
    </View>
  );
}
