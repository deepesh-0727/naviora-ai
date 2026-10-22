import { colors } from '../../shared/theme/colors';
import React, { useCallback, useEffect, useState } from 'react';
import { Alert, ScrollView, Text, TextInput, View } from 'react-native';
import { CommonActions, useNavigation, type NavigationProp } from '@react-navigation/native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Header, Loader, Modal, ScreenContainer } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import { useAuth } from '../../context/AuthContext';
import { useRole } from '../../shared/contexts/RoleContext';
import { clearTokens } from '../../shared/services/secure_store';
import { websocketClient } from '../../shared/services/websocket';

type Entry = Record<string, unknown>;
type ProfileNavigation = NavigationProp<{ StaffSettings: undefined }>;
const PROFILE_PATHS = [
  { key: 'profile', url: '/profile', endpoint: 'GET /staff/profile' },
  { key: 'shift', url: '/shifts/current', endpoint: 'GET /staff/shifts/current' },
  { key: 'attendance', url: '/attendance', endpoint: 'GET /staff/attendance' },
] as const;
function values(value: unknown): Array<[string, string]> {
  if (typeof value !== 'object' || value === null) return [];
  return Object.entries(value).filter(([, item]) => item === null || ['string', 'number', 'boolean'].includes(typeof item))
    .map(([key, item]) => [key.split('_').join(' '), item === null ? '—' : String(item)]);
}
function records(value: unknown): Entry[] {
  if (Array.isArray(value)) return value.filter((item): item is Entry => typeof item === 'object' && item !== null);
  if (typeof value === 'object' && value !== null && 'items' in value && Array.isArray(value.items)) return value.items.filter((item): item is Entry => typeof item === 'object' && item !== null);
  return [];
}

export default function StaffProfile() {
  const navigation = useNavigation<ProfileNavigation>();
  const { signOut } = useAuth();
  const { logout } = useRole();
  const [profile, setProfile] = useState<Entry | null>(null);
  const [shift, setShift] = useState<Entry | null>(null);
  const [attendance, setAttendance] = useState<Entry[]>([]);
  const [missing, setMissing] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<'swap' | 'leave' | null>(null);
  const [requestText, setRequestText] = useState('');
  const [leaveStart, setLeaveStart] = useState('');
  const [leaveEnd, setLeaveEnd] = useState('');
  const [leaveReason, setLeaveReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true); setError(null); setMissing([]);
    const results = await Promise.all(PROFILE_PATHS.map(async (path) => {
      try { return { key: path.key, data: (await apiClient.get<unknown>(buildApiUrl('doctor', path.url))).data, missing: false }; }
      catch (reason: unknown) {
        const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
        if (status === 404 || status === 501) return { key: path.key, data: null, missing: true };
        throw reason;
      }
    }).map((promise) => promise.catch((reason: unknown) => ({ key: 'request-error', data: null, missing: false, reason }))));
    const nextMissing: string[] = [];
    results.forEach((result) => {
      if (result.missing) nextMissing.push(PROFILE_PATHS.find((path) => path.key === result.key)?.endpoint ?? result.key);
      if (result.key === 'profile' && result.data && typeof result.data === 'object') setProfile(result.data as Entry);
      if (result.key === 'shift' && result.data && typeof result.data === 'object') setShift(result.data as Entry);
      if (result.key === 'attendance' && result.data) setAttendance(records(result.data));
    });
    setMissing(nextMissing);
    const failed = results.find((result) => result.key === 'request-error');
    setError(failed ? 'Could not load one or more staff profile sections.' : null);
    setLoading(false);
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  const submitRequest = async () => {
    if (!modal || (modal === 'swap' && !requestText.trim()) || (modal === 'leave' && (!leaveStart.trim() || !leaveEnd.trim() || !leaveReason.trim()))) { setActionError('Enter all required request details first.'); return; }
    setBusy(true); setActionError(null); setActionMessage(null);
    const path = modal === 'swap' ? '/shifts/swap' : '/leave';
    try {
      const payload = modal === 'swap'
        ? { request: requestText.trim() }
        : { start_date: leaveStart.trim(), end_date: leaveEnd.trim(), reason: leaveReason.trim() };
      await apiClient.post(buildApiUrl('doctor', path), payload);
      setActionMessage(modal === 'swap' ? 'Shift swap request submitted.' : 'Leave request submitted.');
      setRequestText(''); setLeaveStart(''); setLeaveEnd(''); setLeaveReason(''); setModal(null); await refresh();
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      setActionError(status === 404 || status === 501 ? `POST /staff${path} is not available on the backend yet.` : 'Could not submit this request.');
    } finally { setBusy(false); }
  };

  const confirmLogout = () => Alert.alert('Log out?', 'You will need to sign in again to access your staff account.', [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Log out', style: 'destructive', onPress: () => { void (async () => {
      websocketClient.disconnect();
      await clearTokens();
      await logout();
      await signOut();
      navigation.getParent()?.dispatch(CommonActions.reset({ index: 0, routes: [{ name: 'RoleSelect' as never }] }));
    })(); } },
  ]);

  if (loading) return <ScreenContainer><Header title="Staff Profile" /><Loader message="Loading staff profile…" /></ScreenContainer>;
  if (error) return <ScreenContainer><Header title="Staff Profile" /><ErrorState message={error} onRetry={() => void refresh()} /></ScreenContainer>;
  return <ScreenContainer><Header title="Staff Profile" /><ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingBottom: 100, gap: 12 }}>
    {missing.map((endpoint) => <BackendNotAvailable key={endpoint} endpoint={endpoint} />)}
    {actionError ? <Text accessibilityRole="alert" style={{ color: colors.danger }}>{actionError}</Text> : null}
    {actionMessage ? <Text style={{ color: colors.primary }}>{actionMessage}</Text> : null}
    {profile ? <Card><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Account</Text>{values(profile).map(([label, value]) => <View key={label} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 }}><Text style={{ color: colors.textMuted, flex: 1 }}>{label}</Text><Text style={{ flex: 1, textAlign: 'right' }}>{value}</Text></View>)}</Card> : null}
    {shift ? <Card><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Current shift</Text>{values(shift).map(([label, value]) => <Text key={label} style={{ paddingVertical: 4 }}>{label}: {value}</Text>)}</Card> : null}
    <Card><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Attendance</Text>{attendance.length ? attendance.map((entry, index) => <Text key={String(entry.id ?? index)} style={{ paddingVertical: 4 }}>{values(entry).map(([label, value]) => `${label}: ${value}`).join(' · ')}</Text>) : <EmptyState message="No attendance records are available." />}</Card>
    <View style={{ gap: 8 }}><Button title="Request shift swap" onPress={() => { setModal('swap'); setActionError(null); }} /><Button title="Request leave" variant="secondary" onPress={() => { setModal('leave'); setActionError(null); }} /><Button title="Staff settings" variant="secondary" onPress={() => navigation.navigate('StaffSettings')} /><Button title="Refresh profile" variant="secondary" onPress={() => void refresh()} /><Button title="Log out" variant="danger" onPress={confirmLogout} /></View>
  </ScrollView><Modal visible={modal !== null}><Card><Text style={{ fontSize: 18, fontWeight: '700', marginBottom: 8 }}>{modal === 'swap' ? 'Shift swap request' : 'Leave request'}</Text>{modal === 'swap' ? <TextInput value={requestText} onChangeText={setRequestText} placeholder="Requested shift and colleague" multiline style={{ minHeight: 80, borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 10, marginBottom: 8 }} /> : <><TextInput value={leaveStart} onChangeText={setLeaveStart} placeholder="Start date (YYYY-MM-DD)" style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 10, marginBottom: 8 }} /><TextInput value={leaveEnd} onChangeText={setLeaveEnd} placeholder="End date (YYYY-MM-DD)" style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 10, marginBottom: 8 }} /><TextInput value={leaveReason} onChangeText={setLeaveReason} placeholder="Reason for leave" multiline style={{ minHeight: 60, borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 10, marginBottom: 8 }} /></>}<View style={{ gap: 8 }}><Button title={busy ? 'Submitting…' : 'Submit request'} disabled={busy} onPress={() => void submitRequest()} /><Button title="Cancel" variant="secondary" disabled={busy} onPress={() => setModal(null)} /></View></Card></Modal></ScreenContainer>;
}
