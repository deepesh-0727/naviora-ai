import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Linking, ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from 'react-native';
import Constants from 'expo-constants';
import { CommonActions, useNavigation } from '@react-navigation/native';
import { useAuth } from '../../context/AuthContext';
import { useRole } from '../../shared/contexts/RoleContext';
import { clearTokens } from '../../shared/services/secure_store';
import { websocketClient } from '../../shared/services/websocket';
import { api } from '../../shared/services/api';
import { BackendNotAvailable, Button, Card, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type Preferences = {
  notifications: { push: boolean; sms: boolean; email: boolean };
  voice: { wake_word: boolean; speed: number };
  language: 'English' | 'Hindi' | 'Tamil';
  privacy: { data_sharing: boolean; analytics: boolean };
};
type RequestError = { response?: { status?: number } };
const DEFAULTS: Preferences = { notifications: { push: true, sms: true, email: true }, voice: { wake_word: false, speed: 1 }, language: 'English', privacy: { data_sharing: false, analytics: false } };
const SUPPORT_URLS = { help: 'https://naviora.ai/help', contact: 'https://naviora.ai/contact', terms: 'https://naviora.ai/terms', privacy: 'https://naviora.ai/privacy' };

function readPreferences(value: Record<string, unknown>): Preferences {
  const notifications = typeof value.notifications === 'object' && value.notifications !== null ? value.notifications as Record<string, unknown> : {};
  const voice = typeof value.voice === 'object' && value.voice !== null ? value.voice as Record<string, unknown> : {};
  const privacy = typeof value.privacy === 'object' && value.privacy !== null ? value.privacy as Record<string, unknown> : {};
  const candidateLanguage = value.language;
  return {
    notifications: { push: typeof notifications.push === 'boolean' ? notifications.push : DEFAULTS.notifications.push, sms: typeof notifications.sms === 'boolean' ? notifications.sms : DEFAULTS.notifications.sms, email: typeof notifications.email === 'boolean' ? notifications.email : DEFAULTS.notifications.email },
    voice: { wake_word: typeof voice.wake_word === 'boolean' ? voice.wake_word : DEFAULTS.voice.wake_word, speed: typeof voice.speed === 'number' ? Math.max(0.5, Math.min(2, voice.speed)) : DEFAULTS.voice.speed },
    language: candidateLanguage === 'Hindi' || candidateLanguage === 'Tamil' ? candidateLanguage : 'English',
    privacy: { data_sharing: typeof privacy.data_sharing === 'boolean' ? privacy.data_sharing : DEFAULTS.privacy.data_sharing, analytics: typeof privacy.analytics === 'boolean' ? privacy.analytics : DEFAULTS.privacy.analytics },
  };
}

export default function SettingsScreen() {
  const navigation = useNavigation();
  const { signOut } = useAuth();
  const { logout: clearRoleSession } = useRole();
  const [settings, setSettings] = useState<Preferences>(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [deleteFlow, setDeleteFlow] = useState(false);
  const [password, setPassword] = useState('');

  const loadSettings = useCallback(async () => {
    setLoading(true); setError(null); setUnavailable(false);
    try { const result = await api.patient.getSettings(); setSettings(readPreferences(result.data)); }
    catch (cause: unknown) { const code = (cause as RequestError).response?.status; if (code === 404 || code === 501) { setUnavailable(true); setSettings(DEFAULTS); } else setError('Could not load settings. Please retry.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void loadSettings(); }, [loadSettings]);

  const saveSettings = async (next: Preferences) => {
    const previous = settings;
    setSettings(next); setSaving(true); setError(null);
    try { const result = await api.patient.updateSettings(next as unknown as Record<string, unknown>); setSettings(readPreferences(result.data)); setUnavailable(false); }
    catch (cause: unknown) {
      const code = (cause as RequestError).response?.status;
      if (code === 404 || code === 501) { setUnavailable(true); setSettings(next); }
      else { setSettings(previous); setError('Could not save this setting. Please try again.'); }
    } finally { setSaving(false); }
  };

  const updateToggle = (section: 'notifications' | 'voice' | 'privacy', key: 'push' | 'sms' | 'email' | 'wake_word' | 'data_sharing' | 'analytics', value: boolean) => {
    if (section === 'voice') void saveSettings({ ...settings, voice: { ...settings.voice, wake_word: value } });
    else if (section === 'notifications') void saveSettings({ ...settings, notifications: { ...settings.notifications, [key]: value } });
    else void saveSettings({ ...settings, privacy: { ...settings.privacy, [key]: value } });
  };

  const logOut = async () => {
    websocketClient.disconnect(); await clearTokens(); await clearRoleSession(); await signOut();
    navigation.getParent()?.dispatch(CommonActions.reset({ index: 0, routes: [{ name: 'RoleSelect' as never }] }));
  };

  const changePassword = () => {
    const root = navigation.getParent();
    root?.dispatch(CommonActions.navigate({ name: 'ResetPassword' }));
  };

  const deleteAccount = () => {
    if (!password.trim()) { setError('Enter your password to delete your account.'); return; }
    Alert.alert('Confirm account deletion', 'This permanently deletes your account and cannot be undone.', [
      { text: 'Keep account', style: 'cancel' },
      { text: 'Delete permanently', style: 'destructive', onPress: () => { void (async () => {
        setSaving(true); setError(null);
        try { await api.patient.deleteAccount(password); setDeleteFlow(false); setPassword(''); await logOut(); }
        catch (cause: unknown) { const code = (cause as RequestError).response?.status; if (code === 404 || code === 501) setUnavailable(true); else setError('Account deletion failed. Check your password and try again.'); }
        finally { setSaving(false); }
      })(); } },
    ]);
  };

  if (loading) return <ScreenContainer><SectionHeader title="Settings" /><Loader message="Loading settings…" /></ScreenContainer>;
  if (error && !unavailable) return <ScreenContainer><SectionHeader title="Settings" /><ErrorState message={error} onRetry={() => void loadSettings()} /></ScreenContainer>;

  const settingsRow = (label: string, value: boolean, onChange: (next: boolean) => void) => <View style={styles.row} key={label}><Text style={styles.rowLabel}>{label}</Text><Switch value={value} onValueChange={onChange} trackColor={{ true: colors.primary }} /></View>;
  return <ScreenContainer style={styles.screen}>
    <SectionHeader title="Settings" />
    {unavailable ? <Card style={styles.unavailable}><BackendNotAvailable endpoint="GET /settings · PUT /settings" /><Button title="Retry" variant="secondary" onPress={() => void loadSettings()} /></Card> : null}
    {error ? <ErrorState message={error} /> : null}
    <ScrollView contentContainerStyle={styles.content}>
      <Card><Text style={styles.heading}>Notifications</Text>{settingsRow('Push notifications', settings.notifications.push, (value) => updateToggle('notifications', 'push', value))}{settingsRow('SMS notifications', settings.notifications.sms, (value) => updateToggle('notifications', 'sms', value))}{settingsRow('Email notifications', settings.notifications.email, (value) => updateToggle('notifications', 'email', value))}</Card>
      <Card><Text style={styles.heading}>Voice Assistant</Text>{settingsRow('Wake word', settings.voice.wake_word, (value) => updateToggle('voice', 'wake_word', value))}<View style={styles.speedWrap}><Text style={styles.rowLabel}>Voice speed</Text><View style={styles.speedControl}><TouchableOpacity accessibilityLabel="Decrease voice speed" disabled={settings.voice.speed <= 0.5} onPress={() => void saveSettings({ ...settings, voice: { ...settings.voice, speed: Math.max(0.5, Math.round((settings.voice.speed - 0.25) * 100) / 100) } })} style={styles.speedButton}><Text style={styles.speedButtonText}>−</Text></TouchableOpacity><Text style={styles.speedValue}>{settings.voice.speed.toFixed(2).replace(/0$/, '')}×</Text><TouchableOpacity accessibilityLabel="Increase voice speed" disabled={settings.voice.speed >= 2} onPress={() => void saveSettings({ ...settings, voice: { ...settings.voice, speed: Math.min(2, Math.round((settings.voice.speed + 0.25) * 100) / 100) } })} style={styles.speedButton}><Text style={styles.speedButtonText}>+</Text></TouchableOpacity></View><View style={styles.scale}><Text>0.5×</Text><View style={styles.scaleLine} /><Text>2×</Text></View></View></Card>
      <Card><Text style={styles.heading}>Language</Text><View style={styles.languages}>{(['English', 'Hindi', 'Tamil'] as const).map((language) => <TouchableOpacity key={language} accessibilityRole="button" onPress={() => void saveSettings({ ...settings, language })} style={[styles.language, settings.language === language && styles.languageSelected]}><Text style={[styles.languageText, settings.language === language && styles.languageTextSelected]}>{language}</Text></TouchableOpacity>)}</View></Card>
      <Card><Text style={styles.heading}>Privacy</Text>{settingsRow('Data sharing', settings.privacy.data_sharing, (value) => updateToggle('privacy', 'data_sharing', value))}{settingsRow('Analytics', settings.privacy.analytics, (value) => updateToggle('privacy', 'analytics', value))}</Card>
      <Card><Text style={styles.heading}>Account</Text><TouchableOpacity onPress={changePassword} style={styles.linkRow}><Text style={styles.rowLabel}>Change Password</Text><Text style={styles.chevron}>›</Text></TouchableOpacity>{deleteFlow ? <><Text style={styles.helper}>Enter your password, then confirm permanent deletion.</Text><TextInput accessibilityLabel="Password for account deletion" value={password} onChangeText={setPassword} placeholder="Password" secureTextEntry style={styles.password} /><Button title={saving ? 'Deleting…' : 'Continue to delete'} variant="danger" disabled={saving} onPress={deleteAccount} /><Button title="Cancel" variant="secondary" onPress={() => { setDeleteFlow(false); setPassword(''); }} style={styles.cancel} /></> : <TouchableOpacity onPress={() => setDeleteFlow(true)} style={styles.linkRow}><Text style={styles.destructive}>Delete Account</Text><Text style={styles.chevron}>›</Text></TouchableOpacity>}</Card>
      <Card><Text style={styles.heading}>Support</Text><LinkRow label="Help & FAQ" url={SUPPORT_URLS.help} /><LinkRow label="Contact Support" url={SUPPORT_URLS.contact} /><LinkRow label="Terms of Service" url={SUPPORT_URLS.terms} /><LinkRow label="Privacy Policy" url={SUPPORT_URLS.privacy} /></Card>
      <Card><Text style={styles.heading}>About</Text><View style={styles.row}><Text style={styles.rowLabel}>App version</Text><Text style={styles.rowValue}>{Constants.expoConfig?.version ?? '—'}</Text></View><View style={styles.row}><Text style={styles.rowLabel}>Build number</Text><Text style={styles.rowValue}>{Constants.expoConfig?.ios?.buildNumber ?? String(Constants.expoConfig?.android?.versionCode ?? '—')}</Text></View></Card>
      <Button title="Log out" variant="secondary" onPress={() => Alert.alert('Log out?', 'You will need to sign in again.', [{ text: 'Cancel', style: 'cancel' }, { text: 'Log out', style: 'destructive', onPress: () => void logOut() }])} />
      {saving ? <Text style={styles.saving}>Saving…</Text> : null}
    </ScrollView>
  </ScreenContainer>;
}

function LinkRow({ label, url }: { label: string; url: string }) { return <TouchableOpacity accessibilityRole="link" onPress={() => void Linking.openURL(url)} style={styles.linkRow}><Text style={styles.rowLabel}>{label}</Text><Text style={styles.chevron}>↗</Text></TouchableOpacity>; }

const styles = StyleSheet.create({ screen: { flex: 1 }, content: { gap: 12, paddingBottom: 24 }, unavailable: { marginBottom: 10 }, heading: { fontSize: 16, fontWeight: '700', color: colors.text, marginBottom: 6 }, row: { minHeight: 48, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomWidth: 1, borderColor: colors.border }, rowLabel: { color: colors.text, flex: 1 }, rowValue: { color: colors.textMuted }, linkRow: { minHeight: 48, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomWidth: 1, borderColor: colors.border }, chevron: { color: colors.textMuted, fontSize: 20, paddingHorizontal: 6 }, speedWrap: { paddingVertical: 12 }, speedControl: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 22, marginVertical: 10 }, speedButton: { width: 38, height: 38, borderRadius: 19, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' }, speedButtonText: { color: colors.primary, fontWeight: '700', fontSize: 20 }, speedValue: { color: colors.text, fontSize: 18, fontWeight: '700', minWidth: 60, textAlign: 'center' }, scale: { flexDirection: 'row', justifyContent: 'space-between', color: colors.textMuted }, scaleLine: { flex: 1, height: 2, backgroundColor: colors.border, alignSelf: 'center', marginHorizontal: 8 }, languages: { flexDirection: 'row', gap: 8 }, language: { borderWidth: 1, borderColor: colors.border, borderRadius: 18, paddingHorizontal: 14, paddingVertical: 9 }, languageSelected: { backgroundColor: colors.primary, borderColor: colors.primary }, languageText: { color: colors.text }, languageTextSelected: { color: colors.white, fontWeight: '700' }, helper: { color: colors.textMuted, marginTop: 4, marginBottom: 8 }, password: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 12, marginBottom: 10, color: colors.text }, destructive: { color: colors.danger, flex: 1 }, cancel: { marginTop: 8 }, saving: { color: colors.textMuted, textAlign: 'center', padding: 8 } });
