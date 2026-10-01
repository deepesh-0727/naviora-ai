import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import {
  FloatingLabelInput,
  NavioraButton,
  NavioraCard,
  NavioraHeader,
  NavioraText,
} from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import { apiService } from '../../services/api';

interface AccountProfile {
  id: number;
  email: string;
  phone: string;
  role: string;
}

export default function NurseProfileScreen() {
  const theme = useTheme();
  const { user, updateUser } = useAuth();
  const [profile, setProfile] = useState<AccountProfile | null>(null);
  const [phone, setPhone] = useState(user?.phone || '');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.get<AccountProfile>('/auth/me');
      if (!result.data) {
        setError(result.error || 'Staff profile is unavailable.');
        return;
      }
      setProfile(result.data);
      setPhone(result.data.phone || '');
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load staff profile.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadProfile(); }, [loadProfile]);

  const saveProfile = async () => {
    const normalizedPhone = phone.trim();
    if (!normalizedPhone) {
      setError('Phone number is required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const result = await apiService.put<AccountProfile>('/auth/me', { phone: normalizedPhone });
      if (result.error || !result.data) {
        setError(result.error || 'Unable to save staff profile.');
        return;
      }
      const updatedProfile = result.data;
      setProfile(current => current ? { ...current, phone: updatedProfile.phone } : current);
      setPhone(updatedProfile.phone);
      setEditing(false);
      await updateUser({ phone: updatedProfile.phone });
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to save staff profile.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <NavioraHeader title="Staff Profile" subtitle="Account contact details" showBack={false} />
        {loading ? <ActivityIndicator color={theme.colors.primary} style={styles.loader} /> : null}
        {error ? <NavioraText color="danger" style={styles.message}>{error}</NavioraText> : null}
        {!loading && !profile && error ? (
          <NavioraButton title="Try again" variant="secondary" onPress={() => void loadProfile()} />
        ) : null}
        {profile ? (
          <NavioraCard style={styles.card}>
            <NavioraText type="h3">{user?.name || 'Staff account'}</NavioraText>
            <NavioraText color="secondary" style={styles.detail}>{profile.email}</NavioraText>
            <NavioraText color="secondary">Role: {profile.role}</NavioraText>
            {editing ? (
              <View style={styles.form}>
                <FloatingLabelInput label="Phone" value={phone} onChangeText={setPhone} keyboardType="phone-pad" />
                <NavioraButton title="Save profile" onPress={saveProfile} loading={saving} />
                <NavioraButton title="Cancel" variant="secondary" onPress={() => { setPhone(profile.phone); setEditing(false); setError(null); }} style={styles.cancelButton} />
              </View>
            ) : (
              <>
                <NavioraText color="secondary" style={styles.detail}>Phone: {profile.phone || 'Not provided'}</NavioraText>
                <NavioraButton title="Edit contact details" onPress={() => { setPhone(profile.phone || ''); setEditing(true); setError(null); }} style={styles.editButton} />
              </>
            )}
          </NavioraCard>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 30 },
  loader: { marginTop: 28 },
  message: { marginVertical: 12 },
  card: { marginTop: 14 },
  detail: { marginTop: 10 },
  form: { marginTop: 16 },
  editButton: { marginTop: 16 },
  cancelButton: { marginTop: 10 },
});
