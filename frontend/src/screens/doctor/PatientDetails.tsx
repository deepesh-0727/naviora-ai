import React from 'react';
import { View } from 'react-native';
import { NavioraHeader, NavioraText, NavioraButton } from '../../components/common/AtomicComponents';

export default function DoctorPatientDetailsScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: '#FAFAF7', padding: 24 }}>
      <NavioraHeader title="Patient Details" subtitle="Full medical history & allergies" />
      <NavioraText type="h3" style={{ marginTop: 20 }}>Alex Morgan</NavioraText>
      <NavioraButton label="Start Telehealth" onPress={() => {}} style={{ marginTop: 20 }} />
    </View>
  );
}
