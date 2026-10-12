import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

import { useTheme } from '../context/ThemeContext';
import { NavioraText } from '../components/common/AtomicComponents';

export default function TelehealthScreen({ navigation }: any) {
  const theme = useTheme();

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <StatusBar style="light" />

      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={28} color={theme.colors.text.high} />
        </TouchableOpacity>
        <NavioraText type="h2">Telehealth</NavioraText>
      </View>

      <View style={styles.content}>
        <View
          style={[
            styles.iconCircle,
            { backgroundColor: theme.colors.primary + '20', borderColor: theme.colors.primary },
          ]}
        >
          <Ionicons name="videocam-off" size={64} color={theme.colors.primary} />
        </View>

        <NavioraText type="h2" style={styles.title}>
          Telehealth Coming Soon
        </NavioraText>

        <NavioraText color="medium" style={styles.message}>
          Secure video consultations will be available in the next app update. For now, please contact
          your doctor through the Appointments screen or visit the hospital directly.
        </NavioraText>

        <TouchableOpacity
          style={[styles.primaryBtn, { backgroundColor: theme.colors.primary }]}
          onPress={() => navigation.navigate('PatientMain', { screen: 'Calendar' })}
        >
          <Ionicons name="calendar" size={20} color="#FFF" />
          <NavioraText type="h3" style={{ color: '#FFF', marginLeft: 8 }}>
            Book In-Person Visit
          </NavioraText>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.secondaryBtn, { borderColor: theme.colors.surfaceVariant }]}
          onPress={() => navigation.goBack()}
        >
          <NavioraText type="h3">Back to Dashboard</NavioraText>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 24,
    borderBottomWidth: 1,
    borderColor: '#1E293B',
  },
  backBtn: { marginRight: 16 },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  iconCircle: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 32,
  },
  title: {
    textAlign: 'center',
    marginBottom: 16,
  },
  message: {
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 40,
  },
  primaryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 16,
    width: '100%',
    marginBottom: 16,
  },
  secondaryBtn: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 16,
    borderWidth: 1,
    width: '100%',
  },
});