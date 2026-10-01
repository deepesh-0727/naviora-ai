import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import {
  FloatingLabelInput,
  NavioraButton,
  NavioraCard,
  NavioraHeader,
  NavioraText,
  NavioraToggle,
} from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import { apiService } from '../../services/api';

interface DoctorProfile {
  id: number;
  first_name: string;
  last_name: string;
  specialization: string;
  years_of_experience: number;
  is_available: boolean;
  email: string;
  phone: string;
}

export default function DoctorProfileScreen() {
  const theme = useTheme();
  const { updateUser } = useAuth();
  const [profile, setProfile] = useState<DoctorProfile | null>(null);
  const [draft, setDraft] = useState<DoctorProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.get<DoctorProfile>('/doctors/profile');
      if (!result.data) {
        setError(result.error || 'Doctor profile is unavailable.');
        return;
      }
      setProfile(result.data);
      setDraft(result.data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load doctor profile.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadProfile(); }, [loadProfile]);

  const saveProfile = async () => {
    if (!draft) return;
    const firstName = draft.first_name.trim();
    const lastName = draft.last_name.trim();
    const specialization = draft.specialization.trim();
    const phone = draft.phone.trim();
    if (!firstName || !lastName || !specialization || !phone) {
      setError('Name, specialization, and phone number are required.');
      return;
    }
    if (!Number.isInteger(Number(draft.years_of_experience)) || draft.years_of_experience < 0) {
      setError('Years of experience must be a non-negative whole number.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const result = await apiService.put<{ message: string }>('/doctors/profile', {
        first_name: firstName,
        last_name: lastName,
        specialization,
        years_of_experience: Number(draft.years_of_experience),
        is_available: draft.is_available,
        phone,
      });
      if (result.error || !result.data) {
        setError(result.error || 'Unable to save doctor profile.');
        return;
      }
      setEditing(false);
      await updateUser({ name: `Dr. ${firstName} ${lastName}`, phone });
      await loadProfile();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to save doctor profile.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <NavioraHeader title="Doctor Profile" subtitle="Professional details and availability" showBack={false} />
        {loading ? <ActivityIndicator color={theme.colors.primary} style={styles.loader} /> : null}
        {error ? <NavioraText color="danger" style={styles.message}>{error}</NavioraText> : null}
        {!loading && !profile && error ? (
          <NavioraButton title="Try again" variant="secondary" onPress={() => void loadProfile()} />
        ) : null}
        {profile && draft ? (
          <NavioraCard style={styles.card}>
            <NavioraText type="h3">{profile.first_name} {profile.last_name}</NavioraText>
            <NavioraText color="secondary">{profile.email}</NavioraText>
            {editing ? (
              <View style={styles.form}>
                <FloatingLabelInput label="First name" value={draft.first_name} onChangeText={(value: string) => setDraft({ ...draft, first_name: value })} />
                <FloatingLabelInput label="Last name" value={draft.last_name} onChangeText={(value: string) => setDraft({ ...draft, last_name: value })} />
                <FloatingLabelInput label="Specialization" value={draft.specialization} onChangeText={(value: string) => setDraft({ ...draft, specialization: value })} />
                <FloatingLabelInput label="Years of experience" value={String(draft.years_of_experience)} onChangeText={(value: string) => setDraft({ ...draft, years_of_experience: Number(value) })} keyboardType="number-pad" />
                <FloatingLabelInput label="Phone" value={draft.phone} onChangeText={(value: string) => setDraft({ ...draft, phone: value })} keyboardType="phone-pad" />
                <View style={styles.availabilityRow}>
                  <NavioraText type="body">Available for appointments</NavioraText>
                  <NavioraToggle value={draft.is_available} onValueChange={(value: boolean) => setDraft({ ...draft, is_available: value })} />
                </View>
                <NavioraButton title="Save profile" onPress={saveProfile} loading={saving} />
                <NavioraButton title="Cancel" variant="secondary" onPress={() => { setDraft(profile); setEditing(false); setError(null); }} style={styles.cancelButton} />
              </View>
            ) : (
              <>
                <NavioraText type="body" style={styles.detail}>{profile.specialization}</NavioraText>
                <NavioraText color="secondary">Experience: {profile.years_of_experience} years</NavioraText>
                <NavioraText color="secondary">Phone: {profile.phone}</NavioraText>
                <NavioraText color="secondary">Availability: {profile.is_available ? 'Available' : 'Unavailable'}</NavioraText>
                <NavioraButton title="Edit profile" onPress={() => { setDraft(profile); setEditing(true); setError(null); }} style={styles.editButton} />
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
  form: { marginTop: 16 },
  detail: { marginTop: 12 },
  availabilityRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginVertical: 14 },
  editButton: { marginTop: 16 },
  cancelButton: { marginTop: 10 },
});
