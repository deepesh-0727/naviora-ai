import React, { useCallback, useEffect, useState } from 'react';
import { Alert, ScrollView, Switch, Text, View } from 'react-native';

import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient, buildApiUrl } from '../../shared/services/api';
import appConfig from '../../../app.json';

type SettingsRecord = Record<string, unknown>;
type DeviceRecord = Record<string, unknown>;
function record(value: unknown): SettingsRecord | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as SettingsRecord : null;
}
function deviceList(value: unknown): DeviceRecord[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is DeviceRecord => typeof item === 'object' && item !== null);
}
function label(key: string): string { return key.split('_').join(' '); }

export default function StaffSettings() {
  const [settings, setSettings] = useState<SettingsRecord | null>(null);
  const [devices, setDevices] = useState<DeviceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true); setError(null); setUnavailable(false);
    try {
      const response = await apiClient.get<unknown>(buildApiUrl('doctor', '/settings'));
      const data = record(response.data);
      if (!data) throw new Error('Settings response was not an object.');
      setSettings(data); setDevices(deviceList(data.devices));
    } catch (reason: unknown) {
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      if (status === 404 || status === 501) setUnavailable(true);
      else setError('Could not load staff settings.');
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  const updateToggle = async (key: string, enabled: boolean) => {
    if (!settings) return;
    const previous = settings;
    const next = { ...settings, [key]: enabled };
    setSettings(next); setSavingKey(key); setActionError(null);
    try {
      const response = await apiClient.put<unknown>(buildApiUrl('doctor', '/settings'), next);
      const saved = record(response.data);
      if (saved) { setSettings(saved); setDevices(deviceList(saved.devices)); }
    } catch (reason: unknown) {
      setSettings(previous);
      const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
      setActionError(status === 404 || status === 501 ? 'Saving staff settings is not available on the backend yet.' : 'Could not save this preference. Retry by changing it again.');
    } finally { setSavingKey(null); }
  };

  const removeDevice = (device: DeviceRecord) => {
    const id = device.id ?? device.device_id;
    if (typeof id !== 'string' && typeof id !== 'number') { setActionError('This device record has no identifier.'); return; }
    Alert.alert('Remove device', 'Sign this device out of your staff account?', [
      { text: 'Keep device', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => { void (async () => {
        setActionError(null);
        try {
          await apiClient.delete(buildApiUrl('doctor', `/devices/${encodeURIComponent(String(id))}`));
          setDevices((current) => current.filter((item) => String(item.id ?? item.device_id) !== String(id)));
        } catch (reason: unknown) {
          const status = typeof reason === 'object' && reason !== null && 'response' in reason ? (reason as { response?: { status?: number } }).response?.status : undefined;
          setActionError(status === 404 || status === 501 ? 'Removing registered devices is not available on the backend yet.' : 'Could not remove this device.');
        }
      })(); } },
    ]);
  };

  if (loading) return <Loader message="Loading staff settings…" />;
  if (unavailable) return <ScreenContainer><BackendNotAvailable endpoint="GET /staff/settings" /><Button title="Retry" variant="secondary" onPress={() => void refresh()} /></ScreenContainer>;
  if (error) return <ErrorState message={error} onRetry={() => void refresh()} />;

  const preferences = Object.entries(settings ?? {}).filter(([, value]) => typeof value === 'boolean');
  return <ScreenContainer><SectionHeader title="Staff Settings" /><ScrollView contentContainerStyle={{ paddingBottom: 24, gap: 12 }}>
    {actionError ? <Text accessibilityRole="alert" style={{ color: '#B42318' }}>{actionError}</Text> : null}
    <Card><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Preferences</Text>{preferences.length ? preferences.map(([key, value]) => <View key={key} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 7 }}><Text style={{ textTransform: 'capitalize', flex: 1 }}>{label(key)}</Text><Switch value={value === true} disabled={savingKey === key} onValueChange={(enabled) => void updateToggle(key, enabled)} /></View>) : <EmptyState message="No toggle preferences are configured for this account." />}</Card>
    <Card><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>Signed-in devices</Text>{devices.length ? devices.map((device, index) => <View key={String(device.id ?? device.device_id ?? index)} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 8 }}><View style={{ flex: 1 }}><Text style={{ fontWeight: '600' }}>{String(device.name ?? device.device_name ?? 'Device')}</Text><Text style={{ color: '#5F6975' }}>{String(device.last_seen ?? device.platform ?? '')}</Text></View><Button title="Remove" variant="danger" onPress={() => removeDevice(device)} /></View>) : <EmptyState message="No other devices are registered." />}</Card>
    <Card><Text style={{ fontSize: 17, fontWeight: '700', marginBottom: 8 }}>About</Text><Text>App version: {appConfig.expo.version}</Text><Text>Build number: Not configured</Text></Card>
    <Button title="Retry settings" variant="secondary" onPress={() => void refresh()} />
  </ScrollView></ScreenContainer>;
}
