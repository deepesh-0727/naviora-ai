import React from 'react';
import { SafeAreaView, ScrollView, StyleSheet } from 'react-native';
import EmergencyActionList from '../../components/common/EmergencyActionList';
import { NavioraHeader } from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';

export default function NurseEmergencyScreen() {
  const theme = useTheme();
  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <NavioraHeader title="Emergency Dispatch" subtitle="Active trauma and escalation events" showBack={false} />
        <EmergencyActionList />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({ screen: { flex: 1 }, content: { padding: 20 } });
