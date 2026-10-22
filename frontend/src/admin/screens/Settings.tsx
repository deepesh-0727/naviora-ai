import React, { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useAlert } from '../../context/AlertContext';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { Button, Card, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type HospitalProfile = { hospital_name: string; contact_phone: string; emergency_line: string };
type SettingRow = { key: string; value: Record<string, unknown> };
const defaults: HospitalProfile = { hospital_name: 'Naviora General', contact_phone: '', emergency_line: '' };

export default function Settings() {
  const { showAlert } = useAlert();
  const [profile, setProfile] = useState<HospitalProfile>(defaults);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<{ items: SettingRow[] }>(buildApiUrl('admin', '/settings'));
      const saved = response.data.items?.find(row => row.key === 'hospital_profile')?.value;
      if (saved) {
        setProfile({
          hospital_name: String(saved.hospital_name ?? defaults.hospital_name),
          contact_phone: String(saved.contact_phone ?? ''),
          emergency_line: String(saved.emergency_line ?? ''),
        });
      }
    } catch {
      setError('Could not load hospital settings.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const save = async () => {
    if (!profile.hospital_name.trim() || !profile.contact_phone.trim() || !profile.emergency_line.trim()) {
      showAlert('Enter a hospital name, contact phone, and emergency line.', 'warning');
      return;
    }
    setSaving(true);
    try {
      await apiClient.put(buildApiUrl('admin', '/settings'), {
        key: 'hospital_profile',
        value: {
          hospital_name: profile.hospital_name.trim(),
          contact_phone: profile.contact_phone.trim(),
          emergency_line: profile.emergency_line.trim(),
        },
      });
      showAlert('Hospital settings updated.', 'success');
    } catch (cause) {
      const message = isAxiosError(cause) ? String(cause.response?.data?.detail ?? 'Could not save hospital settings.') : 'Could not save hospital settings.';
      showAlert(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return <ScreenContainer>
    <SectionHeader title="System settings" />
    <Text style={styles.description}>Hospital contact and emergency details</Text>
    {loading ? <Loader message="Loading settings…" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
      <Card style={styles.card}>
        <Text style={styles.title}>Hospital profile</Text>
        <Text style={styles.label}>Hospital name</Text>
        <TextInput value={profile.hospital_name} onChangeText={hospital_name => setProfile(current => ({ ...current, hospital_name }))} placeholder="Hospital name" placeholderTextColor={colors.textMuted} style={styles.input} />
        <Text style={styles.label}>Contact phone</Text>
        <TextInput value={profile.contact_phone} onChangeText={contact_phone => setProfile(current => ({ ...current, contact_phone }))} keyboardType="phone-pad" placeholder="Contact phone" placeholderTextColor={colors.textMuted} style={styles.input} />
        <Text style={styles.label}>Emergency line</Text>
        <TextInput value={profile.emergency_line} onChangeText={emergency_line => setProfile(current => ({ ...current, emergency_line }))} keyboardType="phone-pad" placeholder="Emergency line" placeholderTextColor={colors.textMuted} style={styles.input} />
        <Button title="Save Settings" loading={saving} disabled={saving} onPress={() => void save()} style={styles.submit} />
      </Card>
      <View style={styles.actions}><Button title="Refresh" variant="secondary" onPress={() => void load()} /></View>
    </ScrollView>}
  </ScreenContainer>;
}

const styles = StyleSheet.create({
  description: { color: colors.textMuted, marginBottom: 10 },
  content: { paddingBottom: 24 },
  card: { marginTop: 8 },
  title: { color: colors.text, fontSize: 17, fontWeight: '700', marginBottom: 5 },
  label: { color: colors.text, fontWeight: '600', marginBottom: 6, marginTop: 12 },
  input: { backgroundColor: colors.white, borderColor: colors.border, borderWidth: 1, borderRadius: 10, color: colors.text, paddingHorizontal: 12, paddingVertical: 11 },
  submit: { marginTop: 18 },
  actions: { marginTop: 12 },
});
