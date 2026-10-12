import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, SafeAreaView, StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '../context/ThemeContext';
import { FloatingLabelInput, GlassCard, GradientButton, NavioraText } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';

export default function ForgotPasswordScreen({ navigation }: any) {
  const theme = useTheme();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const requestReset = async () => {
    const normalizedEmail = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setError('Enter a valid email address.');
      return;
    }

    setError('');
    setLoading(true);
    const result = await apiService.post(
      `/auth/forgot-password?email=${encodeURIComponent(normalizedEmail)}`,
      {},
    );
    setLoading(false);
    if (result.status >= 400 || !result.data) {
      setError(result.error || 'Unable to request a password reset right now.');
      return;
    }
    setSubmitted(true);
  };

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.content}>
          <NavioraText type="h1" color="inverse">Reset password</NavioraText>
          <NavioraText type="body" color="inverse" style={styles.subtitle}>
            Enter the email address on your account and we’ll send a reset link if it’s registered.
          </NavioraText>
          <GlassCard style={styles.card}>
            {submitted ? (
              <NavioraText type="body">
                If that email is registered, a password reset link has been sent. Open the link on this device to continue.
              </NavioraText>
            ) : (
              <>
                <FloatingLabelInput
                  label="Email Address"
                  value={email}
                  onChangeText={setEmail}
                  icon="mail-outline"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  placeholder="you@example.com"
                />
                {error ? <NavioraText type="xs" color="danger" style={styles.error}>{error}</NavioraText> : null}
                <GradientButton title="Send reset link" onPress={requestReset} loading={loading} style={styles.button} />
              </>
            )}
            <GradientButton
              title="Back to sign in"
              variant="secondary"
              onPress={() => navigation.navigate('RoleSelect')}
              style={styles.button}
            />
          </GlassCard>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  content: { flex: 1, justifyContent: 'center', padding: 24 },
  subtitle: { opacity: 0.8, marginTop: 12, marginBottom: 28, lineHeight: 22 },
  card: { padding: 24 },
  error: { marginTop: 12 },
  button: { marginTop: 20 },
});
