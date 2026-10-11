import React, { useState } from 'react';
import { StyleSheet, View, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, SafeAreaView } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

import { useTheme } from '../../context/ThemeContext';
import { NavioraText, NavioraButton } from '../../components/common/AtomicComponents';
import { apiService } from '../../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function OTPScreen({ navigation }: any) {
  const theme = useTheme();
  const [code, setCode] = useState('');
  const [phone, setPhone] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const handleVerify = async () => {
    if (!codeSent) {
      setError('Request a security code before verifying.');
      return;
    }
    if (!phone.trim() || !/^\d{6}$/.test(code)) {
      setError('Enter your phone number and the 6-digit code.');
      return;
    }
    setError('');
    setLoading(true);
    const result = await apiService.post('/auth/otp/verify', { phone, code });
    setLoading(false);
    if (result.status >= 400 || !result.data) { setError(result.error || 'Invalid security code'); return; }
    await AsyncStorage.setItem('otp_verified', 'true');
    navigation.replace('Login', { zone: 'patient' });
  };

  const handleResend = async () => {
    if (!phone.trim()) {
      setError('Enter your phone number before requesting a code.');
      return;
    }
    setError('');
    setNotice('');
    setResending(true);
    const result = await apiService.post(`/auth/otp/generate?phone=${encodeURIComponent(phone.trim())}`, {});
    setResending(false);
    if (result.status >= 400 || !result.data) {
      setError(result.error || 'Unable to resend the security code.');
      return;
    }
    setCodeSent(true);
    setNotice('A new 6-digit security code has been sent.');
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <StatusBar style="light" />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.content}
      >
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={28} color={theme.colors.text.high} />
        </TouchableOpacity>

        <View style={styles.header}>
          <View style={[styles.iconBox, { backgroundColor: theme.colors.secondary + '15' }]}>
            <Ionicons name="shield-checkmark" size={32} color={theme.colors.secondary} />
          </View>
          <NavioraText type="h1">Verify Identity</NavioraText>
          <NavioraText color="medium" style={styles.subtitle}>Enter your phone number and request a security code to verify your identity.</NavioraText>
        </View>

        <TextInput
          style={[styles.phoneInput, { backgroundColor: theme.colors.surface, color: theme.colors.text.high, borderColor: theme.colors.surfaceVariant }]}
          placeholder="Phone number"
          placeholderTextColor={theme.colors.text.low}
          value={phone}
          onChangeText={(value) => {
            setPhone(value);
            setCodeSent(false);
            setCode('');
            setNotice('');
          }}
          keyboardType="phone-pad"
        />
        <TextInput
          style={[styles.otpInput, { backgroundColor: theme.colors.surface, color: theme.colors.text.high, borderColor: theme.colors.surfaceVariant }]}
          maxLength={6}
          keyboardType="number-pad"
          value={code}
          onChangeText={setCode}
          placeholder="000000"
          placeholderTextColor={theme.colors.text.low}
          autoFocus
        />
        {error ? <NavioraText color="primary" style={styles.error}>{error}</NavioraText> : null}
        {notice ? <NavioraText color="secondary" style={styles.error}>{notice}</NavioraText> : null}

        <NavioraButton
          title="Authenticate Session"
          onPress={handleVerify}
          loading={loading}
          style={{ marginTop: 48 }}
        />

        <TouchableOpacity style={styles.resendBtn} onPress={handleResend} disabled={resending}>
          <NavioraText color="medium" type="label">{codeSent ? "DIDN'T RECEIVE CODE? " : 'NEED A SECURITY CODE? '}</NavioraText>
          <NavioraText color="primary" type="label" style={{ textDecorationLine: 'underline' }}>
            {resending ? 'SENDING…' : codeSent ? 'RESEND' : 'SEND CODE'}
          </NavioraText>
        </TouchableOpacity>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { flex: 1, paddingHorizontal: 32, paddingTop: 20 },
  backBtn: { width: 44, height: 44, justifyContent: 'center' },
  header: { alignItems: 'center', marginTop: 40, marginBottom: 48 },
  iconBox: { width: 72, height: 72, borderRadius: 24, justifyContent: 'center', alignItems: 'center', marginBottom: 24 },
  subtitle: { textAlign: 'center', marginTop: 12, lineHeight: 22 },
  otpInput: {
    borderRadius: 20,
    fontSize: 48,
    fontWeight: '900',
    textAlign: 'center',
    width: '100%',
    paddingVertical: 24,
    letterSpacing: 15,
    borderWidth: 1,
  },
  phoneInput: { borderRadius: 16, borderWidth: 1, fontSize: 18, padding: 18, marginBottom: 16 },
  error: { textAlign: 'center', marginTop: 12 },
  resendBtn: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 32,
    alignItems: 'center',
  },
});
