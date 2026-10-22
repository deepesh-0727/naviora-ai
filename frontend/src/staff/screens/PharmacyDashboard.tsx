import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { Card, ScreenContainer, SectionHeader } from '../../shared/components';
import { colors } from '../../shared/theme/colors';

export default function PharmacyDashboard() {
  return (
    <ScreenContainer>
      <SectionHeader title="Pharmacy" />
      <View style={styles.content}>
        <Card style={styles.card}>
          <View style={styles.iconWrap}><Ionicons name="medkit-outline" size={42} color={colors.primary} /></View>
          <Text style={styles.title}>Pharmacy Management</Text>
          <Text style={styles.message}>Pharmacy Management is coming in Phase 2.</Text>
        </Card>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  content: { flex: 1, justifyContent: 'center', paddingBottom: 24 },
  card: { alignItems: 'center', paddingVertical: 32, paddingHorizontal: 20 },
  iconWrap: { width: 88, height: 88, borderRadius: 44, backgroundColor: colors.primaryLight, alignItems: 'center', justifyContent: 'center', marginBottom: 18 },
  title: { color: colors.text, fontSize: 19, fontWeight: '700', marginBottom: 8, textAlign: 'center' },
  message: { color: colors.textMuted, fontSize: 15, textAlign: 'center', lineHeight: 22 },
});
