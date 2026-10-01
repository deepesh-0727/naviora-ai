import React, { useEffect, useState } from 'react';
import { StyleSheet, View, ScrollView, TouchableOpacity, SafeAreaView, ActivityIndicator, Image } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInUp } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { NavioraText, GlassCard, StatusBadge, FloatingLabelInput, NavioraButton } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';

interface PatientProfile {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  blood_group?: string;
  allergies?: string[] | null;
  medical_history?: string;
  insurance_provider?: string;
  insurance_number?: string;
  emergency_contact_name: string;
  emergency_contact: string;
  avatar_url?: string;
}

export default function ProfileScreen({ navigation }: any) {
  const theme = useTheme();
  const { signOut, updateUser } = useAuth();
  const [patientData, setPatientData] = useState<PatientProfile | null>(null);
  const [draft, setDraft] = useState<PatientProfile | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.get<PatientProfile>('/patients/profile');
      if (res.data) {
        setPatientData(res.data);
      } else {
        setError(res.error || 'Failed to load profile.');
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load profile.');
    } finally {
      setLoading(false);
    }
  };

  const beginEditing = () => {
    if (!patientData) return;
    setDraft({ ...patientData, allergies: patientData.allergies || [] });
    setError(null);
    setEditing(true);
  };

  const saveProfile = async () => {
    if (!draft) return;
    const firstName = draft.first_name.trim();
    const lastName = draft.last_name.trim();
    const contactName = draft.emergency_contact_name.trim();
    const contactPhone = draft.emergency_contact.trim();
    if (!firstName || !lastName || !contactName || !contactPhone) {
      setError('First name, last name, and emergency contact name and phone are required.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const result = await apiService.put<{ message: string }>('/patients/profile', {
        first_name: firstName,
        last_name: lastName,
        blood_group: draft.blood_group?.trim() || null,
        allergies: (Array.isArray(draft.allergies) ? draft.allergies : [])
          .flatMap(value => value.split(','))
          .map(value => value.trim())
          .filter(Boolean),
        emergency_contact: contactPhone,
        emergency_contact_name: contactName,
        medical_history: draft.medical_history?.trim() || null,
        insurance_provider: draft.insurance_provider?.trim() || null,
        insurance_number: draft.insurance_number?.trim() || null,
      });
      if (result.error || !result.data) {
        setError(result.error || 'Unable to save profile changes.');
        return;
      }
      setEditing(false);
      await updateUser({ name: `${firstName} ${lastName}` });
      await fetchProfile();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to save profile changes.');
    } finally {
      setSaving(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    navigation.replace('Login');
  };

  const ProfileSection = ({ title, children }: any) => (
    <View style={styles.section}>
      <NavioraText type="label" color="low" style={styles.sectionTitle}>{title.toUpperCase()}</NavioraText>
      <GlassCard style={{ padding: 8 }}>{children}</GlassCard>
    </View>
  );

  const InfoRow = ({ label, value, icon, color = theme.colors.primary, isLast = false }: any) => (
    <View style={[styles.infoRow, !isLast && styles.divider]}>
      <View style={[styles.infoIcon, { backgroundColor: color + '20' }]}>
        <Ionicons name={icon} size={20} color={color} />
      </View>
      <View style={{ flex: 1, marginLeft: 16 }}>
        <NavioraText type="xs" color="low">{label}</NavioraText>
        <NavioraText type="label">{value || '—'}</NavioraText>
      </View>
    </View>
  );

  const SettingItem = ({ icon, label, onPress, isDestructive = false }: any) => (
    <TouchableOpacity onPress={onPress} style={styles.settingItem}>
      <View style={[styles.settingIcon, { backgroundColor: isDestructive ? theme.colors.error + '20' : 'rgba(255,255,255,0.05)' }]}>
        <Ionicons name={icon} size={20} color={isDestructive ? theme.colors.error : '#FFF'} />
      </View>
      <NavioraText type="label" style={[{ flex: 1, marginLeft: 16 }, isDestructive && { color: theme.colors.error }]}>{label}</NavioraText>
      <Ionicons name="chevron-forward" size={18} color={theme.colors.text.low} />
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
        <SafeAreaView style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color="#FFF" />
          <NavioraText type="body" color="inverse" style={{ marginTop: 16 }}>Loading profile...</NavioraText>
        </SafeAreaView>
      </LinearGradient>
    );
  }

  if (error && !patientData) {
    return (
      <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
        <SafeAreaView style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 }}>
          <Ionicons name="alert-circle-outline" size={64} color={theme.colors.error} />
          <NavioraText type="h3" style={{ marginTop: 16, textAlign: 'center' }}>{error}</NavioraText>
          <TouchableOpacity onPress={fetchProfile} style={[styles.retryBtn, { borderColor: theme.colors.primary }]}>
            <NavioraText type="label" color="primary">Retry</NavioraText>
          </TouchableOpacity>
        </SafeAreaView>
      </LinearGradient>
    );
  }

  const fullName = patientData
    ? `${patientData.first_name || ''} ${patientData.last_name || ''}`.trim()
    : '';

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.header}>
          <NavioraText type="h2">My Profile</NavioraText>
          <TouchableOpacity style={styles.iconBtn} onPress={editing ? () => setEditing(false) : beginEditing}>
            <Ionicons name={editing ? 'close' : 'create-outline'} size={24} color="#FFF" />
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          <Animated.View entering={FadeInUp} style={styles.profileHeader}>
            <View style={[styles.avatarContainer, { borderColor: theme.colors.primary }]}>
              {patientData?.avatar_url ? (
                <Image source={{ uri: patientData.avatar_url }} style={styles.avatar} />
              ) : (
                <View style={[styles.avatar, { backgroundColor: theme.colors.primary + '30', justifyContent: 'center', alignItems: 'center' }]}>
                  <Ionicons name="person" size={56} color={theme.colors.primary} />
                </View>
              )}
              <View style={[styles.badgeContainer, { backgroundColor: theme.colors.primary }]}>
                <Ionicons name="checkmark-circle" size={20} color="#FFF" />
              </View>
            </View>
            <NavioraText type="h1" style={{ marginTop: 20 }}>{fullName || 'Patient'}</NavioraText>
            <NavioraText type="body" color="low">
              ID: {patientData?.id ? `NAV-${String(patientData.id).padStart(5, '0')}` : '—'}
            </NavioraText>
            {patientData?.blood_group && (
              <View style={{ marginTop: 12 }}>
                <StatusBadge text={`Blood Group: ${patientData.blood_group}`} color="accent" />
              </View>
            )}
          </Animated.View>

          {error ? <NavioraText type="caption" color="danger" style={{ marginBottom: 16 }}>{error}</NavioraText> : null}
          {editing && draft ? (
            <ProfileSection title="Edit Profile">
              <FloatingLabelInput label="First name" value={draft.first_name} onChangeText={(value: string) => setDraft({ ...draft, first_name: value })} />
              <FloatingLabelInput label="Last name" value={draft.last_name} onChangeText={(value: string) => setDraft({ ...draft, last_name: value })} />
              <FloatingLabelInput label="Blood group" value={draft.blood_group || ''} onChangeText={(value: string) => setDraft({ ...draft, blood_group: value })} />
              <FloatingLabelInput label="Allergies (comma separated)" value={(draft.allergies || []).join(', ')} onChangeText={(value: string) => setDraft({ ...draft, allergies: [value] })} />
              <FloatingLabelInput label="Medical history" value={draft.medical_history || ''} onChangeText={(value: string) => setDraft({ ...draft, medical_history: value })} multiline numberOfLines={3} textAlignVertical="top" />
              <FloatingLabelInput label="Insurance provider" value={draft.insurance_provider || ''} onChangeText={(value: string) => setDraft({ ...draft, insurance_provider: value })} />
              <FloatingLabelInput label="Insurance number" value={draft.insurance_number || ''} onChangeText={(value: string) => setDraft({ ...draft, insurance_number: value })} />
              <FloatingLabelInput label="Emergency contact name" value={draft.emergency_contact_name} onChangeText={(value: string) => setDraft({ ...draft, emergency_contact_name: value })} />
              <FloatingLabelInput label="Emergency contact phone" value={draft.emergency_contact} onChangeText={(value: string) => setDraft({ ...draft, emergency_contact: value })} keyboardType="phone-pad" />
              <NavioraButton title="Save profile" onPress={saveProfile} loading={saving} style={{ marginTop: 12 }} />
            </ProfileSection>
          ) : null}

          {!editing && <>
          <ProfileSection title="Medical Information">
            <InfoRow
              label="Allergies"
              value={patientData?.allergies?.join(', ') || 'None recorded'}
              icon="alert-circle"
              color={theme.colors.error}
            />
            <InfoRow
              label="Medical History"
              value={patientData?.medical_history || 'None recorded'}
              icon="medical"
              color={theme.colors.primary}
            />
            <InfoRow
              label="Insurance"
              value={
                patientData?.insurance_provider
                  ? `${patientData.insurance_provider}${patientData.insurance_number ? ` (${patientData.insurance_number})` : ''}`
                  : 'Not provided'
              }
              icon="card"
              color={theme.colors.accent}
              isLast
            />
          </ProfileSection>

          <ProfileSection title="Contact Information">
            <InfoRow label="Email" value={patientData?.email} icon="mail-outline" />
            <InfoRow label="Phone" value={patientData?.phone || 'Not provided'} icon="call-outline" isLast />
          </ProfileSection>

          {(patientData?.emergency_contact_name || patientData?.emergency_contact) ? (
            <ProfileSection title="Emergency Contact">
              <View style={styles.emergencyCard}>
                <View style={{ flex: 1 }}>
                  <NavioraText type="h3">{patientData.emergency_contact_name || '—'}</NavioraText>
                  <NavioraText type="xs" color="low">{patientData.emergency_contact || '—'}</NavioraText>
                </View>
                <TouchableOpacity style={[styles.callBtn, { backgroundColor: theme.colors.error }]}>
                  <Ionicons name="call" size={20} color="#FFF" />
                </TouchableOpacity>
              </View>
            </ProfileSection>
          ) : (
            <ProfileSection title="Emergency Contact">
              <View style={styles.emergencyCard}>
                <NavioraText type="body" color="low">No emergency contact added.</NavioraText>
              </View>
            </ProfileSection>
          )}

          <ProfileSection title="Settings">
            <SettingItem icon="settings-outline" label="Account Settings" onPress={() => navigation.navigate('Settings')} />
            <SettingItem icon="notifications-outline" label="Notifications" onPress={() => navigation.navigate('Alerts')} />
            <SettingItem icon="shield-checkmark-outline" label="Privacy & Security" />
            <SettingItem icon="help-circle-outline" label="Help & Support" />
            <SettingItem icon="log-out-outline" label="Logout" isDestructive onPress={handleSignOut} />
          </ProfileSection>
          </>}

          <View style={{ height: 120 }} />
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 24 },
  iconBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  scrollContent: { paddingHorizontal: 24 },
  profileHeader: { alignItems: 'center', marginVertical: 32 },
  avatarContainer: { position: 'relative', width: 120, height: 120, borderRadius: 60, borderWidth: 3, padding: 4 },
  avatar: { width: '100%', height: '100%', borderRadius: 60 },
  badgeContainer: { position: 'absolute', bottom: 0, right: 0, width: 32, height: 32, borderRadius: 16, justifyContent: 'center', alignItems: 'center', borderWidth: 3, borderColor: '#0A1628' },
  section: { marginBottom: 32 },
  sectionTitle: { letterSpacing: 1.5, marginBottom: 16, fontWeight: '800' },
  infoRow: { flexDirection: 'row', alignItems: 'center', padding: 16 },
  infoIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  divider: { borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.05)' },
  emergencyCard: { flexDirection: 'row', alignItems: 'center', padding: 16 },
  callBtn: { width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center' },
  settingItem: { flexDirection: 'row', alignItems: 'center', padding: 16 },
  settingIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  retryBtn: { marginTop: 24, paddingHorizontal: 32, paddingVertical: 12, borderRadius: 12, borderWidth: 1 },
});
