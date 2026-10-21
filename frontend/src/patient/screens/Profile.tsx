import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Image, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
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
      const data = result.data as ProfileRecord | null | undefined;
      if (!data || typeof data !== 'object') {
        console.log('PROFILE FETCH FAILED: response did not contain a profile object');
        setProfile(null);
        setError('Could not load your profile. Please try again.');
        return;
      }
      console.log('PROFILE SUCCESS FIELDS:', Object.keys(data));
      setProfile(data);
      setDraft({ first_name: data.first_name ?? '', last_name: data.last_name ?? '', date_of_birth: data.date_of_birth ?? '', gender: data.gender ?? '', blood_group: data.blood_group ?? '', phone: data.phone ?? '', email: data.email ?? '', emergency_contact_name: data.emergency_contact_name ?? '', emergency_contact: data.emergency_contact ?? '', allergies: Array.isArray(data.allergies) ? data.allergies.join(', ') : '', insurance_provider: data.insurance_provider ?? '', insurance_number: data.insurance_number ?? '' });
    } catch (cause: unknown) {
      const code = (cause as RequestError).response?.status;
      console.log('PROFILE FETCH FAILED:', cause instanceof Error ? cause.message : String(cause), 'HTTP STATUS:', code ?? 'none');
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
    const dateOfBirth = dob ? dob.slice(0, 10) : null;
    if (phone && !/^\d{10}$/.test(phone)) { setError('Enter a valid 10-digit Indian phone number.'); return; }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError('Enter a valid email address.'); return; }
    if (dob && (!/^\d{4}-\d{2}-\d{2}$/.test(dateOfBirth ?? '') || Number.isNaN(Date.parse(`${dateOfBirth}T00:00:00`)) || new Date(`${dateOfBirth}T00:00:00`) > new Date())) { setError('Enter a valid date of birth in YYYY-MM-DD format that is not in the future.'); return; }
    setSaving(true); setError(null);
    try {
      const response = await api.patient.updateProfile({ ...draft, date_of_birth: dateOfBirth, gender: draft.gender.trim().toLowerCase() || null, blood_group: draft.blood_group.replace(/\s+/g, '').toUpperCase() || null, phone: phone || null, email: email || null, emergency_contact_name: draft.emergency_contact_name.trim() || null, emergency_contact: draft.emergency_contact.trim() || null, allergies: draft.allergies.split(',').map((item) => item.trim()).filter(Boolean) });
      setProfile((current) => current ? { ...current, ...response.data.data } : response.data.data);
      setError(null);
      setEditing(false);
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

  if (loading) return <ScreenContainer><SectionHeader title="Patient Medical Profile" /><Loader message="Loading profile…" /></ScreenContainer>;
  if (unavailable) return <ScreenContainer><SectionHeader title="Patient Medical Profile" /><BackendNotAvailable endpoint="GET /patients/profile" /><Button title="Retry" variant="secondary" onPress={() => void loadProfile()} /></ScreenContainer>;
  if (error && !profile) return <ScreenContainer><SectionHeader title="Patient Medical Profile" /><ErrorState message={error} onRetry={() => void loadProfile()} /></ScreenContainer>;
  if (!profile) return <ScreenContainer><SectionHeader title="Patient Medical Profile" /><EmptyState message="No profile information is available." /><Button title="Retry" variant="secondary" onPress={() => void loadProfile()} /></ScreenContainer>;

  const fullName = `${profile.first_name} ${profile.last_name}`.trim();
  return <ScreenContainer>
    <View style={styles.header}><View><SectionHeader title="Patient Medical Profile" /><Text style={styles.subtitle}>Health records and emergency contacts</Text></View><TouchableOpacity accessibilityRole="button" accessibilityLabel="App preferences" onPress={() => navigation.navigate('Settings' as never)} style={styles.settings}><Ionicons name="settings-outline" size={21} color={colors.primary} /></TouchableOpacity></View>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
      <Card style={styles.identity}><View style={styles.identityRow}>{profile.avatar_url ? <Image source={{ uri: profile.avatar_url }} style={styles.avatar} /> : <Avatar label={fullName || 'Patient'} size={68} />}<View style={styles.identityCopy}><Text style={styles.name}>{fullName || 'Patient'}</Text><Text style={styles.patientId}>Patient ID: {profile.id}</Text><Text style={styles.sub}>{profile.phone || profile.email || ''}</Text></View>{profile.blood_group ? <View style={styles.blood}><Ionicons name="water" size={13} color={colors.danger} /><Text style={styles.bloodText}>{profile.blood_group}</Text></View> : null}</View></Card>
      {error ? <ErrorState message={error} /> : null}
      {editing ? <Card>
        <SectionHeader title="Personal details" />
        {(['first_name', 'last_name', 'date_of_birth', 'gender', 'blood_group', 'phone', 'email', 'emergency_contact_name', 'emergency_contact', 'allergies', 'insurance_provider', 'insurance_number'] as const).map((key) => <View key={key} style={styles.field}><Text style={styles.label}>{FIELD_LABELS[key]}</Text><TextInput accessibilityLabel={FIELD_LABELS[key]} value={draft[key]} onChangeText={(value) => setField(key, value)} placeholder={FIELD_LABELS[key]} keyboardType={key === 'phone' || key === 'emergency_contact' ? 'phone-pad' : key === 'email' ? 'email-address' : 'default'} autoCapitalize={key === 'email' ? 'none' : 'sentences'} style={styles.input} />{key === 'date_of_birth' ? <Text style={styles.help}>Use YYYY-MM-DD</Text> : null}</View>)}
        <Button title={saving ? 'Saving…' : 'Save changes'} disabled={saving} onPress={() => void saveProfile()} />
      </Card> : <>
        <Card><Text style={styles.sectionTitle}>Clinical Information</Text><View style={styles.detailsRow}><View style={styles.detail}><Text style={styles.label}>Date of birth</Text><Text style={styles.value}>{dateLabel(profile.date_of_birth)}</Text></View><View style={styles.detail}><Text style={styles.label}>Gender</Text><Text style={styles.value}>{profile.gender || '—'}</Text></View><View style={styles.detail}><Text style={styles.label}>Blood group</Text><Text style={[styles.value, styles.bloodAccent]}>{profile.blood_group || '—'}</Text></View></View><InfoRow label="Phone" value={profile.phone} /><InfoRow label="Email" value={profile.email} /><View style={styles.divider} /><Text style={styles.label}>Documented allergies</Text><Text style={styles.value}>{profile.allergies?.length ? profile.allergies.join(' · ') : 'None recorded'}</Text><View style={styles.divider} /><Text style={styles.label}>Past medical history</Text><Text style={styles.value}>{profile.medical_history || 'No history recorded'}</Text></Card>
        <Card><Text style={styles.sectionTitle}>Insurance Coverage</Text><View style={styles.inline}><View style={styles.softIcon}><Ionicons name="shield-checkmark-outline" size={22} color={colors.primary} /></View><View style={styles.detail}><Text style={styles.value}>{profile.insurance_provider || 'No provider recorded'}</Text><Text style={styles.sub}>{profile.insurance_number ? `Policy: ${profile.insurance_number}` : 'Policy details unavailable'}</Text></View></View></Card>
        <Card><Text style={styles.sectionTitle}>Emergency Contact</Text><View style={styles.inline}><View style={[styles.softIcon, styles.dangerIcon]}><Ionicons name="heart" size={20} color={colors.danger} /></View><View style={styles.detail}><Text style={styles.value}>{profile.emergency_contact_name || 'No contact recorded'}</Text><Text style={styles.sub}>{profile.emergency_contact || 'Add an emergency contact in Edit Profile'}</Text></View></View></Card>
      </>}
      <Card style={styles.stats}><Text style={styles.statTitle}>Account activity</Text><InfoRow label="Total visits" value={profile.total_visits === undefined || profile.total_visits === null ? null : String(profile.total_visits)} /><InfoRow label="Last visit" value={dateLabel(profile.last_visit_date)} /><TouchableOpacity onPress={() => { setEditing((value) => !value); setError(null); }} style={styles.editAction}><Ionicons name="create-outline" size={18} color={colors.primary} /><Text style={styles.action}>{editing ? 'Cancel editing' : 'Edit profile details'}</Text></TouchableOpacity></Card>
      <Button title="Log out" variant="danger" onPress={handleLogout} style={styles.logout} />
    </ScrollView>
  </ScreenContainer>;
}

const FIELD_LABELS: Record<FieldName, string> = { first_name: 'First name', last_name: 'Last name', date_of_birth: 'Date of birth', gender: 'Gender', blood_group: 'Blood group', phone: 'Phone', email: 'Email', emergency_contact_name: 'Emergency contact name', emergency_contact: 'Emergency contact phone', allergies: 'Allergies (comma separated)', insurance_provider: 'Insurance provider', insurance_number: 'Insurance number' };
const styles = StyleSheet.create({ header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }, subtitle: { color: colors.textMuted, marginTop: -4, marginBottom: 10 }, settings: { width: 42, height: 42, borderRadius: 21, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' }, action: { color: colors.primary, fontWeight: '700', padding: 8 }, content: { gap: 14, paddingBottom: 24 }, identity: { paddingVertical: 18 }, identityRow: { flexDirection: 'row', alignItems: 'center', gap: 12 }, identityCopy: { flex: 1 }, avatar: { width: 68, height: 68, borderRadius: 34 }, name: { color: colors.text, fontSize: 20, fontWeight: '800' }, patientId: { color: colors.primary, fontWeight: '700', marginTop: 4 }, sub: { color: colors.textMuted, marginTop: 4 }, blood: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 9, paddingVertical: 6, borderRadius: 10, backgroundColor: colors.dangerLight }, bloodText: { color: colors.danger, fontWeight: '800' }, sectionTitle: { color: colors.text, fontSize: 18, fontWeight: '800', marginBottom: 12 }, detailsRow: { flexDirection: 'row', paddingBottom: 10, marginBottom: 6, borderBottomWidth: 1, borderColor: colors.border }, detail: { flex: 1 }, value: { color: colors.text, fontWeight: '600', lineHeight: 21 }, bloodAccent: { color: colors.danger }, divider: { height: 1, backgroundColor: colors.border, marginVertical: 12 }, inline: { flexDirection: 'row', alignItems: 'center', gap: 12 }, softIcon: { width: 48, height: 48, borderRadius: 16, backgroundColor: colors.primaryLight, alignItems: 'center', justifyContent: 'center' }, dangerIcon: { backgroundColor: colors.dangerLight }, editAction: { flexDirection: 'row', alignItems: 'center', marginTop: 8, alignSelf: 'flex-start' }, field: { marginBottom: 12 }, label: { color: colors.textMuted, fontSize: 13, marginBottom: 5 }, input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 11, backgroundColor: colors.background, color: colors.text }, help: { color: colors.textMuted, fontSize: 12, marginTop: 4 }, stats: { marginBottom: 4 }, statTitle: { color: colors.text, fontWeight: '700', fontSize: 16, marginBottom: 5 }, logout: { marginTop: 4 } });
