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
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInDown, FadeInUp } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import {
  NavioraText,
  GlassCard,
  GradientButton,
  FloatingLabelInput,
  StatusBadge,
} from '../components/common/AtomicComponents';

export default function LoginScreen({ navigation }: any) {
  const theme = useTheme();
  const { loginWithCredentials } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (loading) return;
    setError('');
    if (!email.trim()) { setError('Please enter your email address.'); return; }
    if (!password.trim()) { setError('Please enter your password.'); return; }

    setLoading(true);
    const result = await loginWithCredentials(email.trim(), password);
    setLoading(false);

    if (!result.success) {
      setError(result.error || 'Unable to sign in. Please check your credentials.');
      return;
    }
    navigation.replace('Main');
  };

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.kav}>
          <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
            <Animated.View entering={FadeInDown.delay(200).duration(800)} style={styles.header}>
              <View style={styles.logoRow}>
                <View style={[styles.logoIcon, { backgroundColor: 'rgba(255,255,255,0.15)', borderColor: 'rgba(255,255,255,0.3)' }]}>
                  <Ionicons name="pulse" size={32} color="#FFF" />
                </View>
                <NavioraText type="h2" color="inverse" style={{ marginLeft: 12 }}>Naviora AI</NavioraText>
              </View>
              <NavioraText type="h1" color="inverse" style={styles.welcomeText}>Welcome Back</NavioraText>
              <NavioraText type="body" color="inverse" style={{ opacity: 0.75 }}>Sign in to continue your healthcare journey</NavioraText>
            </Animated.View>

            <Animated.View entering={FadeInUp.delay(400).duration(800)}>
              <GlassCard style={styles.formCard}>
                <View style={styles.formHeader}>
                  <NavioraText type="label" color="low">SECURE ACCESS</NavioraText>
                  <StatusBadge text="HIPAA" color="accent" icon="shield-checkmark" />
                </View>

                <FloatingLabelInput
                  label="Email Address"
                  value={email}
                  onChangeText={setEmail}
                  icon="mail-outline"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  placeholder="you@example.com"
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

              {/* Register CTA */}
              <GlassCard style={styles.registerCard}>
                <NavioraText type="body" color="low" style={{ textAlign: 'center', marginBottom: 16 }}>
                  Don't have an account?
                </NavioraText>
                <TouchableOpacity
                  style={[styles.registerBtn, { borderColor: 'rgba(255,255,255,0.3)' }]}
                  onPress={() => navigation.navigate('Register')}
                >
                  <Ionicons name="mic" size={20} color="#FFF" style={{ marginRight: 10 }} />
                  <NavioraText type="label" color="inverse">Register with Voice AI</NavioraText>
                </TouchableOpacity>
              </GlassCard>
            </Animated.View>

            <View style={styles.footer}>
              <Ionicons name="shield-checkmark" size={16} color={theme.colors.primaryLight} />
              <NavioraText type="xs" color="inverse" style={{ marginLeft: 6, opacity: 0.6 }}>Secure • Private • Encrypted</NavioraText>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  kav: { flex: 1 },
  scroll: { flexGrow: 1, padding: 24, justifyContent: 'center' },
  header: { marginBottom: 28 },
  logoRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  logoIcon: { width: 56, height: 56, borderRadius: 18, borderWidth: 1, justifyContent: 'center', alignItems: 'center' },
  welcomeText: { marginTop: 8, marginBottom: 4 },
  formCard: { paddingVertical: 24, marginBottom: 16 },
  formHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  forgotBtn: { alignSelf: 'flex-end', marginBottom: 24 },
  errorBox: { flexDirection: 'row', alignItems: 'center', padding: 12, borderRadius: 12, borderWidth: 1, marginTop: 16 },
  registerCard: { padding: 20, marginBottom: 16, alignItems: 'center' },
  registerBtn: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 24, borderRadius: 14, borderWidth: 1.5, width: '100%', justifyContent: 'center' },
  footer: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: 8 },
});
