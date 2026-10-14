import React from 'react';
import { Text, View } from 'react-native';

import { BackendNotAvailable, ScreenContainer, SectionHeader } from '../../shared/components';

export interface StaffModuleScreenProps {
  title: string;
  endpoint: string;
}

export default function StaffModuleScreen({ title, endpoint }: StaffModuleScreenProps) {
  return (
    <ScreenContainer>
      <SectionHeader title={title} />
      <View style={{ flex: 1 }}>
        <BackendNotAvailable endpoint={endpoint} />
      </View>
      <Text accessibilityRole="text" style={{ color: '#5F6975', textAlign: 'center' }}>
        This staff screen will be completed in its feature batch.
      </Text>
    </ScreenContainer>
  );
}
