import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  View,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import Animated, { FadeInDown, FadeInUp } from 'react-native-reanimated';

import { useTheme } from '../../context/ThemeContext';
import { COLORS } from '../../shared/theme';
import { useAuth, type LoginZone } from '../../context/AuthContext';
import {
  NavioraText,
  GlassCard,
  GradientButton,
  FloatingLabelInput,
  StatusBadge,
} from '../../components/common/AtomicComponents';

export default function LoginScreen({ navigation, route }: any) {
  const theme = useTheme();
  const { loginWithCredentials } = useAuth();
  const requestedZone = route?.params?.zone;
  const zone: LoginZone = requestedZone === 'staff' || requestedZone === 'admin' ? requestedZone : 'patient';
  const zoneTitle = zone === 'patient' ? 'Patient' : zone === 'staff' ? 'Healthcare Staff' : 'Administrator';
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (loading) return;
    setError('');
    if (!identifier.trim()) { setError('Enter your email address or phone number.'); return; }
    if (!password.trim()) { setError('Please enter your password.'); return; }

    setLoading(true);
    let result: { success: boolean; error?: string };
    try {
      result = await loginWithCredentials(identifier.trim(), password, zone);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Unable to sign in. Please try again.');
      setLoading(false);
      return;
    }
    setLoading(false);

    if (!result.success) {
      setError(result.error || 'Unable to sign in. Please check your credentials.');
      return;
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <StatusBar style="dark" />
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.kav}>
          <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
            <Animated.View entering={FadeInDown.delay(200).duration(800)} style={styles.header}>
              <TouchableOpacity onPress={() => navigation.navigate('RoleSelect')} style={styles.backToRoles}>
                <Ionicons name="chevron-back" size={18} color={COLORS.primary} />
                <NavioraText type="label" color="primary" style={{ marginLeft: 4 }}>Change account type</NavioraText>
              </TouchableOpacity>
              <View style={styles.logoRow}>
                <View style={[styles.logoIcon, { backgroundColor: COLORS.primaryLight, borderColor: COLORS.border }]}>
                  <Ionicons name="pulse" size={32} color={COLORS.primary} />
                </View>
                <NavioraText type="h2" color="primary" style={{ marginLeft: 12 }}>Naviora AI</NavioraText>
              </View>
              <NavioraText type="h1" color="primary" style={styles.welcomeText}>Welcome to Naviora AI</NavioraText>
              <NavioraText type="body" color="low">{zoneTitle} · Hospital coordination and voice assistant</NavioraText>
            </Animated.View>

            <Animated.View entering={FadeInUp.delay(400).duration(800)}>
              <GlassCard style={styles.formCard}>
                <View style={styles.formHeader}>
              <NavioraText type="label" color="low">SECURE ACCESS</NavioraText>
                  <StatusBadge text="HIPAA" color="accent" icon="shield-checkmark" />
                </View>

                <FloatingLabelInput
                  label={zone === 'staff' ? 'Staff email or phone number' : 'Email or phone number'}
                  value={identifier}
                  onChangeText={setIdentifier}
                  icon="person-outline"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  placeholder="you@example.com or +91 98765 43210"
                />
                <FloatingLabelInput
                  label="Password"
                  value={password}
                  onChangeText={setPassword}
                  icon="lock-closed-outline"
                  secureTextEntry
                  placeholder="••••••••"
                />

                <TouchableOpacity style={styles.forgotBtn} onPress={() => navigation.navigate('ForgotPassword')}>
                  <NavioraText type="label" color="primary">Forgot Password?</NavioraText>
                </TouchableOpacity>

                <GradientButton title="Sign In" onPress={handleLogin} loading={loading} style={{ marginTop: 10 }} />

                {!!error && (
                  <View style={[styles.errorBox, { borderColor: theme.colors.error + '40', backgroundColor: theme.colors.error + '10' }]}>
                    <Ionicons name="alert-circle" size={16} color={theme.colors.error} />
                    <NavioraText type="xs" style={{ color: theme.colors.error, marginLeft: 8, flex: 1 }}>{error}</NavioraText>
                  </View>
                )}
              </GlassCard>

              {zone === 'patient' ? (
              <GlassCard style={styles.registerCard}>
                  <TouchableOpacity
                    accessibilityRole="button"
                    onPress={() => navigation.navigate('Registration')}
                    style={{ marginBottom: 16 }}
                  >
                    <NavioraText type="body" color="low" style={{ textAlign: 'center' }}>
                      Don't have an account?
                    </NavioraText>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.registerBtn, { backgroundColor: theme.colors.primary, borderColor: theme.colors.primary }]}
                    onPress={() => navigation.navigate('Registration')}
                  >
                    <Ionicons name="person-add-outline" size={20} color={COLORS.white} style={{ marginRight: 10 }} />
                    <NavioraText type="label" color="inverse">Create Account</NavioraText>
                  </TouchableOpacity>
                </GlassCard>
              ) : null}
            </Animated.View>

            <View style={styles.footer}>
              <Ionicons name="shield-checkmark" size={16} color={theme.colors.primary} />
              <NavioraText type="xs" color="low" style={{ marginLeft: 6 }}>Secure • Private • Encrypted</NavioraText>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  kav: { flex: 1 },
  scroll: { flexGrow: 1, padding: 24, justifyContent: 'center' },
  header: { marginBottom: 28 },
  backToRoles: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', marginBottom: 18 },
  logoRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  logoIcon: { width: 56, height: 56, borderRadius: 18, borderWidth: 1, justifyContent: 'center', alignItems: 'center' },
  welcomeText: { marginTop: 8, marginBottom: 4 },
  formCard: { paddingVertical: 24, marginBottom: 16 },
  formHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  forgotBtn: { alignSelf: 'flex-end', marginBottom: 24 },
  errorBox: { flexDirection: 'row', alignItems: 'center', padding: 12, borderRadius: 12, borderWidth: 1, marginTop: 16 },
  registerCard: { padding: 20, marginBottom: 16, alignItems: 'center' },
  registerBtn: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 24, borderRadius: 999, borderWidth: 1.5, width: '100%', justifyContent: 'center' },
  footer: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: 8 },
});
