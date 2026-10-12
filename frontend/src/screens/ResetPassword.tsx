import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, SafeAreaView, StyleSheet } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { LinearGradient } from 'expo-linear-gradient';
import { useRoute } from '@react-navigation/native';
import { useTheme } from '../context/ThemeContext';
import { FloatingLabelInput, GlassCard, GradientButton, NavioraText } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';

export default function ResetPasswordScreen({ navigation }: any) {
  const theme = useTheme();
  const route = useRoute<any>();
  const token = typeof route.params?.token === 'string' ? route.params.token : '';
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState(token ? '' : 'This reset link is missing its token. Request a new link.');
  const [loading, setLoading] = useState(false);

  const resetPassword = async () => {
    if (!token) return;
    if (password.length < 8) {
      setError('Use at least 8 characters for your new password.');
      return;
    }
    if (password !== confirmation) {
      setError('The passwords do not match.');
      return;
    }
    setError('');
    setLoading(true);
    const result = await apiService.post('/auth/reset-password', { token, new_password: password });
    setLoading(false);
    if (result.status >= 400 || !result.data) {
      setError(result.error || 'Unable to reset your password. Request a new link and try again.');
      return;
    }
    navigation.replace('RoleSelect');
  };

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.content}>
          <NavioraText type="h1" color="inverse">Choose a new password</NavioraText>
          <NavioraText type="body" color="inverse" style={styles.subtitle}>
            Set a new password for your Naviora AI account.
          </NavioraText>
          <GlassCard style={styles.card}>
            <FloatingLabelInput
              label="New Password"
              value={password}
              onChangeText={setPassword}
              icon="lock-closed-outline"
              secureTextEntry
              autoCapitalize="none"
            />
            <FloatingLabelInput
              label="Confirm Password"
              value={confirmation}
              onChangeText={setConfirmation}
              icon="lock-closed-outline"
              secureTextEntry
              autoCapitalize="none"
            />
            {error ? <NavioraText type="xs" color="danger" style={styles.error}>{error}</NavioraText> : null}
            <GradientButton title="Update password" onPress={resetPassword} loading={loading} disabled={!token} style={styles.button} />
            <GradientButton
              title="Request a new link"
              variant="secondary"
              onPress={() => navigation.navigate('ForgotPassword')}
              style={styles.button}
            />
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
  subtitle: { opacity: 0.8, marginTop: 12, marginBottom: 28 },
  card: { padding: 24 },
  error: { marginTop: 12 },
  button: { marginTop: 20 },
});
