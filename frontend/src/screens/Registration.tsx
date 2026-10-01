import React, { useState } from 'react';
import { StyleSheet, View, ScrollView, TouchableOpacity, SafeAreaView, KeyboardAvoidingView, Platform } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInRight, FadeOutLeft } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { NavioraText, GlassCard, GradientButton, FloatingLabelInput } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';

export default function RegistrationScreen({ navigation }: any) {
  const theme = useTheme();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ phone: '', email: '', first_name: '', last_name: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const setField = (field: keyof typeof form, value: string) => setForm(current => ({ ...current, [field]: value }));

  const continueRegistration = async () => {
    setError('');
    if (step < 3) {
      setStep(current => current + 1);
      return;
    }

    setLoading(true);
    try {
      const result = await apiService.post('/auth/register', form);
      if (result.status >= 400 || !result.data) {
        setError(result.error || 'Registration failed');
        return;
      }
      navigation.replace('Login');
    } catch {
      setError('Unable to reach services.');
    } finally {
      setLoading(false);
    }
  };

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <Animated.View entering={FadeInRight} exiting={FadeOutLeft} key="step1">
            <NavioraText type="h3" style={styles.stepTitle}>Let's start with your contact info</NavioraText>
            <FloatingLabelInput
              label="Phone Number"
              value={form.phone}
              onChangeText={(v: string) => setField('phone', v)}
              icon="call-outline"
              keyboardType="phone-pad"
              placeholder="+91 98765 43210"
            />
            <FloatingLabelInput
              label="Email Address"
              value={form.email}
              onChangeText={(v: string) => setField('email', v)}
              icon="mail-outline"
              keyboardType="email-address"
              placeholder="patient@example.com"
            />
          </Animated.View>
        );
      case 2:
        return (
          <Animated.View entering={FadeInRight} exiting={FadeOutLeft} key="step2">
            <NavioraText type="h3" style={styles.stepTitle}>What should we call you?</NavioraText>
            <FloatingLabelInput
              label="First Name"
              value={form.first_name}
              onChangeText={(v: string) => setField('first_name', v)}
              icon="person-outline"
              placeholder="John"
            />
            <FloatingLabelInput
              label="Last Name"
              value={form.last_name}
              onChangeText={(v: string) => setField('last_name', v)}
              icon="person-outline"
              placeholder="Doe"
            />
          </Animated.View>
        );
      case 3:
        return (
          <Animated.View entering={FadeInRight} exiting={FadeOutLeft} key="step3">
            <NavioraText type="h3" style={styles.stepTitle}>Secure your account</NavioraText>
            <FloatingLabelInput
              label="Password"
              value={form.password}
              onChangeText={(v: string) => setField('password', v)}
              icon="lock-closed-outline"
              secureTextEntry
              placeholder="••••••••"
            />
            <NavioraText type="xs" color="low" style={styles.hint}>Use at least 8 characters with a mix of letters and numbers.</NavioraText>
          </Animated.View>
        );
      default:
        return null;
    }
  };

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => (step > 1 ? setStep(step - 1) : navigation.goBack())} style={styles.backBtn}>
            <Ionicons name={step > 1 ? "arrow-back" : "close"} size={28} color="#FFF" />
          </TouchableOpacity>
          <View style={styles.progressBarContainer}>
            <View style={[styles.progressBar, { backgroundColor: theme.colors.glass.bg }]}>
              <View style={[styles.progressFill, { width: `${(step / 3) * 100}%`, backgroundColor: theme.colors.primary }]} />
            </View>
          </View>
        </View>

        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
          <ScrollView contentContainerStyle={styles.scrollContent}>
            <NavioraText type="h1" style={styles.title}>Create Account</NavioraText>
            <NavioraText type="body" color="low" style={styles.subtitle}>Join the future of clinical orchestration.</NavioraText>

            <GlassCard style={styles.card}>
              {renderStep()}

              {error ? (
                <View style={[styles.errorBox, { borderColor: theme.colors.error + '40', backgroundColor: theme.colors.error + '10' }]}>
                  <NavioraText type="xs" style={{ color: theme.colors.error }}>{error}</NavioraText>
                </View>
              ) : null}

              <GradientButton
                title={step === 3 ? "Create Account" : "Continue"}
                onPress={continueRegistration}
                loading={loading}
                style={{ marginTop: 20 }}
              />

              <TouchableOpacity style={styles.voiceBtn}>
                <Ionicons name="mic" size={20} color={theme.colors.primary} />
                <NavioraText type="label" color="primary" style={{ marginLeft: 8 }}>Register via Voice AI</NavioraText>
              </TouchableOpacity>
            </GlassCard>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', padding: 24 },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  progressBarContainer: { flex: 1, marginLeft: 20 },
  progressBar: { height: 6, borderRadius: 3, overflow: 'hidden' },
  progressFill: { height: '100%' },
  scrollContent: { padding: 24 },
  title: { marginBottom: 8 },
  subtitle: { marginBottom: 32 },
  card: { paddingVertical: 24 },
  stepTitle: { marginBottom: 24 },
  hint: { marginTop: -10, marginBottom: 20, marginLeft: 4 },
  errorBox: { padding: 12, borderRadius: 12, borderWidth: 1, marginBottom: 16 },
  voiceBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 24 },
});
