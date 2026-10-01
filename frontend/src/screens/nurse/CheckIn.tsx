import React from 'react';
import { View } from 'react-native';
import { NavioraHeader, NavioraText, NavioraButton } from '../../components/common/AtomicComponents';

export default function NurseCheckInScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: '#FAFAF7', padding: 24 }}>
      <NavioraHeader title="Patient Check-in" subtitle="Search by name or ID" />
      <NavioraText type="h3" style={{ marginTop: 20 }}>Check-in queue</NavioraText>
      <NavioraButton label="Confirm Check-in" onPress={() => {}} style={{ marginTop: 20 }} />
    </View>
  );
}
