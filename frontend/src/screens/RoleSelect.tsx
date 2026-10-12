import React from 'react';
import { SafeAreaView, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '../context/ThemeContext';
import { GlassCard, NavioraText } from '../components/common/AtomicComponents';

type LoginZone = 'patient' | 'staff' | 'admin';

const zones: { id: LoginZone; title: string; description: string; icon: React.ComponentProps<typeof Ionicons>['name']; color: string }[] = [
  {
    id: 'patient',
    title: 'Patient',
    description: 'Appointments, care updates, and hospital services',
    icon: 'heart',
    color: '#3B82F6',
  },
  {
    id: 'staff',
    title: 'Healthcare Staff',
    description: 'Clinical workflows for doctors, nurses, and staff',
    icon: 'medkit',
    color: '#10B981',
  },
  {
    id: 'admin',
    title: 'Administrator',
    description: 'Hospital operations and system management',
    icon: 'business',
    color: '#8B5CF6',
  },
];

export default function RoleSelectScreen({ navigation }: any) {
  const theme = useTheme();

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.brand}>
            <View style={styles.logo}>
              <Ionicons name="pulse" size={32} color="#FFF" />
            </View>
            <NavioraText type="h1" color="inverse" style={styles.title}>Naviora AI</NavioraText>
            <NavioraText type="body" color="inverse" style={styles.subtitle}>
              Choose the account type you use to sign in.
            </NavioraText>
          </View>

          <View style={styles.zoneList}>
            {zones.map(zone => (
              <TouchableOpacity
                key={zone.id}
                accessibilityRole="button"
                onPress={() => navigation.navigate('Login', { zone: zone.id })}
                activeOpacity={0.86}
              >
                <GlassCard style={styles.zoneCard}>
                  <View style={[styles.zoneIcon, { backgroundColor: `${zone.color}20` }]}>
                    <Ionicons name={zone.icon} size={26} color={zone.color} />
                  </View>
                  <View style={styles.zoneText}>
                    <NavioraText type="h3">{zone.title}</NavioraText>
                    <NavioraText type="xs" color="low" style={styles.description}>{zone.description}</NavioraText>
                  </View>
                  <Ionicons name="chevron-forward" size={22} color={theme.colors.text.low} />
                </GlassCard>
              </TouchableOpacity>
            ))}
          </View>

          <NavioraText type="xs" color="inverse" style={styles.disclaimer}>
            Your role and access are verified by your account after sign-in.
          </NavioraText>
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  content: { flexGrow: 1, justifyContent: 'center', padding: 24 },
  brand: { alignItems: 'center', marginBottom: 40 },
  logo: {
    width: 72,
    height: 72,
    borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 18,
  },
  title: { marginBottom: 8 },
  subtitle: { opacity: 0.78, textAlign: 'center' },
  zoneList: { gap: 14 },
  zoneCard: { flexDirection: 'row', alignItems: 'center', padding: 18 },
  zoneIcon: { width: 52, height: 52, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  zoneText: { flex: 1, marginHorizontal: 16 },
  description: { marginTop: 4 },
  disclaimer: { opacity: 0.65, textAlign: 'center', marginTop: 28 },
});
