import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Image, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { CommonActions, useNavigation } from '@react-navigation/native';
import { useAuth } from '../../context/AuthContext';
import { useRole } from '../../shared/contexts/RoleContext';
import { clearTokens } from '../../shared/services/secure_store';
import { websocketClient } from '../../shared/services/websocket';
import { api, type PatientProfile as PatientProfileData } from '../../shared/services/api';
import { Avatar, BackendNotAvailable, Button, Card, EmptyState, ErrorState, InfoRow, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type ProfileRecord = PatientProfileData & { avatar_url?: string | null; total_visits?: number | null; last_visit_date?: string | null };
type RequestError = { response?: { status?: number } };
type FieldName = 'first_name' | 'last_name' | 'date_of_birth' | 'gender' | 'blood_group' | 'phone' | 'email' | 'emergency_contact_name' | 'emergency_contact' | 'allergies' | 'insurance_provider' | 'insurance_number';
type ProfileDraft = Record<FieldName, string>;

const blankDraft: ProfileDraft = { first_name: '', last_name: '', date_of_birth: '', gender: '', blood_group: '', phone: '', email: '', emergency_contact_name: '', emergency_contact: '', allergies: '', insurance_provider: '', insurance_number: '' };
const dateLabel = (value?: string | null) => value ? new Date(value).toLocaleDateString() : '—';

export default function ProfileScreen() {
  const navigation = useNavigation();
  const { signOut } = useAuth();
  const { logout: clearRoleSession } = useRole();
  const [profile, setProfile] = useState<ProfileRecord | null>(null);
  const [draft, setDraft] = useState<ProfileDraft>(blankDraft);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  const loadProfile = useCallback(async () => {
    setLoading(true); setError(null); setUnavailable(false);
    try {
      const result = await api.patient.getProfile();
      const data = result.data as ProfileRecord;
      setProfile(data);
      setDraft({ first_name: data.first_name ?? '', last_name: data.last_name ?? '', date_of_birth: data.date_of_birth ?? '', gender: data.gender ?? '', blood_group: data.blood_group ?? '', phone: data.phone ?? '', email: data.email ?? '', emergency_contact_name: data.emergency_contact_name ?? '', emergency_contact: data.emergency_contact ?? '', allergies: data.allergies?.join(', ') ?? '', insurance_provider: data.insurance_provider ?? '', insurance_number: data.insurance_number ?? '' });
    } catch (cause: unknown) {
      const code = (cause as RequestError).response?.status;
      if (code === 404 || code === 501) setUnavailable(true);
      else setError('Could not load your profile. Please try again.');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void loadProfile(); }, [loadProfile]);

  const setField = (key: FieldName, value: string) => setDraft((previous) => ({ ...previous, [key]: value }));
  const saveProfile = async () => {
    const email = draft.email.trim();
    const phone = draft.phone.replace(/\D/g, '');
    const dob = draft.date_of_birth.trim();
    if (phone && !/^\d{10}$/.test(phone)) { setError('Enter a valid 10-digit Indian phone number.'); return; }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError('Enter a valid email address.'); return; }
    if (dob && (Number.isNaN(Date.parse(dob)) || new Date(dob) > new Date())) { setError('Enter a valid date of birth that is not in the future.'); return; }
    setSaving(true); setError(null);
    try {
      await api.patient.updateProfile({ ...draft, phone: phone || null, email: email || null, allergies: draft.allergies.split(',').map((item) => item.trim()).filter(Boolean) });
      setEditing(false);
      await loadProfile();
    } catch (cause: unknown) {
      const code = (cause as RequestError).response?.status;
      if (code === 404 || code === 501) setUnavailable(true);
      else setError('Could not save your profile. Please try again.');
    } finally { setSaving(false); }
  };

  const handleLogout = () => Alert.alert('Log out?', 'You will need to sign in again to access your account.', [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Log out', style: 'destructive', onPress: () => { void (async () => {
      websocketClient.disconnect();
      await clearTokens();
      await clearRoleSession();
      await signOut();
      navigation.getParent()?.getParent()?.dispatch(CommonActions.reset({ index: 0, routes: [{ name: 'RoleSelect' as never }] }));
    })(); } },
  ]);

  if (loading) return <ScreenContainer><SectionHeader title="Profile" /><Loader message="Loading profile…" /></ScreenContainer>;
  if (unavailable) return <ScreenContainer><SectionHeader title="Profile" /><BackendNotAvailable endpoint="GET /patients/profile" /><Button title="Retry" variant="secondary" onPress={() => void loadProfile()} /></ScreenContainer>;
  if (error && !profile) return <ScreenContainer><SectionHeader title="Profile" /><ErrorState message={error} onRetry={() => void loadProfile()} /></ScreenContainer>;
  if (!profile) return <ScreenContainer><SectionHeader title="Profile" /><EmptyState message="No profile information is available." /><Button title="Retry" variant="secondary" onPress={() => void loadProfile()} /></ScreenContainer>;

  const fullName = `${profile.first_name} ${profile.last_name}`.trim();
  return <ScreenContainer>
    <View style={styles.header}><SectionHeader title="Profile" /><TouchableOpacity onPress={() => { setEditing((value) => !value); setError(null); }}><Text style={styles.action}>{editing ? 'Cancel' : 'Edit'}</Text></TouchableOpacity></View>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
      <Card style={styles.identity}>{profile.avatar_url ? <Image source={{ uri: profile.avatar_url }} style={styles.avatar} /> : <Avatar label={fullName || 'Patient'} size={72} />}<Text style={styles.name}>{fullName || 'Patient'}</Text><Text style={styles.sub}>{profile.email || profile.phone || ''}</Text></Card>
      {error ? <ErrorState message={error} /> : null}
      {editing ? <Card>
        <SectionHeader title="Personal details" />
        {(['first_name', 'last_name', 'date_of_birth', 'gender', 'blood_group', 'phone', 'email', 'emergency_contact_name', 'emergency_contact', 'allergies', 'insurance_provider', 'insurance_number'] as const).map((key) => <View key={key} style={styles.field}><Text style={styles.label}>{FIELD_LABELS[key]}</Text><TextInput accessibilityLabel={FIELD_LABELS[key]} value={draft[key]} onChangeText={(value) => setField(key, value)} placeholder={FIELD_LABELS[key]} keyboardType={key === 'phone' || key === 'emergency_contact' ? 'phone-pad' : key === 'email' ? 'email-address' : 'default'} autoCapitalize={key === 'email' ? 'none' : 'sentences'} style={styles.input} />{key === 'date_of_birth' ? <Text style={styles.help}>Use YYYY-MM-DD</Text> : null}</View>)}
        <Button title={saving ? 'Saving…' : 'Save changes'} disabled={saving} onPress={() => void saveProfile()} />
      </Card> : <Card>
        <SectionHeader title="Personal and health details" />
        <InfoRow label="Date of birth" value={dateLabel(profile.date_of_birth)} /><InfoRow label="Gender" value={profile.gender} /><InfoRow label="Blood group" value={profile.blood_group} /><InfoRow label="Phone" value={profile.phone} /><InfoRow label="Email" value={profile.email} /><InfoRow label="Emergency contact" value={[profile.emergency_contact_name, profile.emergency_contact].filter(Boolean).join(' · ')} /><InfoRow label="Allergies" value={profile.allergies?.join(', ')} /><InfoRow label="Insurance" value={[profile.insurance_provider, profile.insurance_number].filter(Boolean).join(' · ')} />
      </Card>}
      <Card style={styles.stats}><Text style={styles.statTitle}>Account activity</Text><InfoRow label="Total visits" value={profile.total_visits === undefined || profile.total_visits === null ? null : String(profile.total_visits)} /><InfoRow label="Last visit" value={dateLabel(profile.last_visit_date)} /></Card>
      <Button title="Log out" variant="danger" onPress={handleLogout} style={styles.logout} />
    </ScrollView>
  </ScreenContainer>;
}

const FIELD_LABELS: Record<FieldName, string> = { first_name: 'First name', last_name: 'Last name', date_of_birth: 'Date of birth', gender: 'Gender', blood_group: 'Blood group', phone: 'Phone', email: 'Email', emergency_contact_name: 'Emergency contact name', emergency_contact: 'Emergency contact phone', allergies: 'Allergies (comma separated)', insurance_provider: 'Insurance provider', insurance_number: 'Insurance number' };
const styles = StyleSheet.create({ header: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' }, action: { color: colors.primary, fontWeight: '700', padding: 8 }, content: { gap: 14, paddingBottom: 24 }, identity: { alignItems: 'center', paddingVertical: 22 }, avatar: { width: 72, height: 72, borderRadius: 36 }, name: { color: colors.text, fontSize: 20, fontWeight: '700', marginTop: 10 }, sub: { color: colors.textMuted, marginTop: 4 }, field: { marginBottom: 12 }, label: { color: colors.textMuted, fontSize: 13, marginBottom: 5 }, input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 11, backgroundColor: colors.background, color: colors.text }, help: { color: colors.textMuted, fontSize: 12, marginTop: 4 }, stats: { marginBottom: 4 }, statTitle: { color: colors.text, fontWeight: '700', fontSize: 16, marginBottom: 5 }, logout: { marginTop: 4 } });
