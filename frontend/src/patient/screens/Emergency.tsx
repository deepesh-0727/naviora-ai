import React, { useEffect, useRef, useState } from 'react';
import { Animated, Linking, Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import * as Location from 'expo-location';
import { useRole } from '../../shared/contexts/RoleContext';
import { api } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';
import { BackendNotAvailable, Card, ErrorState, InfoRow, ScreenContainer, SectionHeader } from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type EmergencyEvent = { id?: number; status?: string };
type RequestError = { response?: { status?: number } };

export default function EmergencyScreen() {
  const { user } = useRole();
  const [holding, setHolding] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [caseId, setCaseId] = useState<number | null>(null);
  const [timeline, setTimeline] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [locationDenied, setLocationDenied] = useState(false);
  const [cancelAvailable, setCancelAvailable] = useState(false);
  const progress = useRef(new Animated.Value(0)).current;
  const holdTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const triggeredAt = useRef<number | null>(null);

  useEffect(() => {
    void websocketClient.connect();
    const subscribe = (event: string, label: string) => websocketClient.subscribe(event, (payload: unknown) => {
      const data = payload as EmergencyEvent;
      if (caseId !== null && data.id !== undefined && data.id !== caseId) return;
      setTimeline((steps) => steps.includes(label) ? steps : [...steps, label]);
    });
    const unsubs = [subscribe('emergency_ack', 'Emergency signal acknowledged'), subscribe('emergency_en_route', 'Help is on the way'), subscribe('emergency_arrived', 'Responders have arrived')];
    return () => { unsubs.forEach((unsubscribe) => unsubscribe()); if (holdTimer.current) clearTimeout(holdTimer.current); if (cancelTimer.current) clearTimeout(cancelTimer.current); };
  }, [caseId]);

  const triggerEmergency = async () => {
    setTriggering(true); setError(null); setUnavailable(false); setLocationDenied(false);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== 'granted') { setLocationDenied(true); return; }
      const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      const response = await api.patient.triggerEmergency({ location: { lat: position.coords.latitude, lng: position.coords.longitude }, patient_id: user?.id, condition: undefined });
      setCaseId(response.data.id); setTimeline(['Emergency signal sent']); triggeredAt.current = Date.now(); setCancelAvailable(true);
      cancelTimer.current = setTimeout(() => { triggeredAt.current = null; setCancelAvailable(false); }, 30000);
    } catch (cause: unknown) {
      const code = (cause as RequestError).response?.status;
      if (code === 404 || code === 501) setUnavailable(true);
      else if (cause instanceof Error && /location|gps|provider/i.test(cause.message)) setLocationDenied(true);
      else setError('Could not send your emergency signal. Please try again.');
    } finally { setTriggering(false); setHolding(false); progress.stopAnimation(); progress.setValue(0); }
  };

  const startHold = () => {
    if (caseId !== null || triggering) return;
    setHolding(true); progress.setValue(0);
    Animated.timing(progress, { toValue: 1, duration: 2000, useNativeDriver: false }).start();
    holdTimer.current = setTimeout(() => void triggerEmergency(), 2000);
  };
  const cancelHold = () => { if (holdTimer.current) clearTimeout(holdTimer.current); holdTimer.current = null; setHolding(false); progress.stopAnimation(); progress.setValue(0); };

  const cancelEmergency = async () => {
    if (caseId === null || triggeredAt.current === null || Date.now() - triggeredAt.current > 30000) return;
    try { await api.patient.cancelEmergency(caseId); setTimeline((steps) => [...steps, 'Emergency cancelled']); triggeredAt.current = null; setCancelAvailable(false); }
    catch { setError('Could not cancel the emergency request. Please try again.'); }
  };

  return <ScreenContainer>
    <SectionHeader title="Emergency" />
    <Text style={styles.explainer}>Hold the SOS button for 2 seconds to send your location to the response team.</Text>
    <View style={styles.sosArea}><Animated.View style={[styles.ring, { transform: [{ scale: progress.interpolate({ inputRange: [0, 1], outputRange: [1, 1.35] }) }], opacity: progress.interpolate({ inputRange: [0, 1], outputRange: [0.25, 0.75] }) }]} /><TouchableOpacity accessibilityRole="button" accessibilityLabel="Hold for two seconds to trigger emergency" onPressIn={startHold} onPressOut={cancelHold} disabled={triggering || caseId !== null} style={styles.sos}><Text style={styles.sosText}>{triggering ? '…' : holding ? 'HOLD' : 'SOS'}</Text></TouchableOpacity></View>
    {locationDenied ? <Card><Text style={styles.warning}>Enable location to send accurate emergency signal.</Text><TouchableOpacity onPress={() => Platform.OS === 'ios' ? void Linking.openURL('app-settings:') : void Linking.openSettings()}><Text style={styles.link}>Open Settings</Text></TouchableOpacity></Card> : null}
    {unavailable ? <BackendNotAvailable endpoint="POST /emergency/trigger" /> : null}
    {error ? <ErrorState message={error} onRetry={() => setError(null)} /> : null}
    <Card style={styles.card}><Text style={styles.cardTitle}>Critical information</Text><InfoRow label="Name" value={user?.name} /><InfoRow label="Blood group" value={typeof user?.blood_group === 'string' ? user.blood_group : null} /><InfoRow label="Allergies" value={Array.isArray(user?.allergies) ? user.allergies.join(', ') : null} /><InfoRow label="Emergency contact" value={typeof user?.emergency_contact === 'string' ? user.emergency_contact : null} /></Card>
    {timeline.length ? <Card style={styles.card}><Text style={styles.cardTitle}>Response status</Text>{timeline.map((step, index) => <Text style={styles.step} key={`${step}-${index}`}>●  {step}</Text>)}{cancelAvailable ? <TouchableOpacity onPress={() => void cancelEmergency()} style={styles.cancel}><Text style={styles.cancelText}>Cancel request</Text></TouchableOpacity> : null}</Card> : null}
  </ScreenContainer>;
}

const styles = StyleSheet.create({ explainer: { color: colors.textMuted, textAlign: 'center', marginBottom: 12 }, sosArea: { height: 185, alignItems: 'center', justifyContent: 'center' }, ring: { position: 'absolute', width: 120, height: 120, borderRadius: 60, backgroundColor: colors.danger }, sos: { width: 112, height: 112, borderRadius: 56, backgroundColor: colors.danger, alignItems: 'center', justifyContent: 'center', elevation: 5 }, sosText: { color: '#fff', fontSize: 26, fontWeight: '800' }, card: { marginTop: 14 }, cardTitle: { color: colors.text, fontWeight: '700', fontSize: 16, marginBottom: 6 }, step: { paddingVertical: 8, color: colors.text }, cancel: { marginTop: 12, alignSelf: 'center', padding: 10 }, cancelText: { color: colors.danger, fontWeight: '700' }, warning: { color: colors.text }, link: { color: colors.primary, paddingTop: 10, fontWeight: '700' } });
