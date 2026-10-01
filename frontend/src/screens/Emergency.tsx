import React, { useState, useRef, useEffect } from 'react';
import { ActivityIndicator, StyleSheet, View, TouchableOpacity, ScrollView, SafeAreaView } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as Location from 'expo-location';
import Animated, { FadeInDown, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { NavioraText, GlassCard, PulseAnimation } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';

export default function EmergencyScreen({ navigation }: any) {
  const theme = useTheme();
  const [activated, setActivated] = useState(false);
  const [isHolding, setIsHolding] = useState(false);
  const [emergencyId, setEmergencyId] = useState<number | null>(null);
  const [responders, setResponders] = useState<any[]>([]);
  const [locationLabel, setLocationLabel] = useState('Location unavailable');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const holdProgress = useSharedValue(0);
  const holdTimer = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => () => {
    if (holdTimer.current) clearTimeout(holdTimer.current);
  }, []);

  const triggerEmergency = async () => {
    setSubmitting(true);
    setError(null);
    let location = 'Location unavailable';
    let coordinates: { latitude: number; longitude: number } | null = null;
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status === 'granted') {
        const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
        coordinates = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };
        location = `${coordinates.latitude},${coordinates.longitude}`;
      }
    } catch {
      // The SOS request remains available when device location is unavailable.
    }
    setLocationLabel(location);
    try {
      const result = await apiService.post<{ emergency_id: number }>('/emergency/trigger', {
        location,
        description: 'Patient SOS - Immediate Assistance Required',
      });
      if (result.error || !result.data?.emergency_id) {
        setError(result.error || 'The emergency alert could not be confirmed. Please retry.');
        holdProgress.value = withTiming(0, { duration: 250 });
        return;
      }
      setEmergencyId(result.data.emergency_id);
      setActivated(true);
      if (coordinates) {
        const staffRes = await apiService.get<{ staff?: any[] }>(
          `/emergency/nearby-staff?latitude=${coordinates.latitude}&longitude=${coordinates.longitude}`
        );
        if (staffRes.data?.staff) setResponders(staffRes.data.staff);
        else if (staffRes.error) setError(staffRes.error);
      }
    } catch (triggerError) {
      setError(triggerError instanceof Error ? triggerError.message : 'Unable to send the emergency alert.');
    } finally {
      setSubmitting(false);
    }
  };

  const handlePressIn = () => {
    if (submitting || activated) return;
    setIsHolding(true);
    holdProgress.value = withTiming(1, { duration: 3000 });
    holdTimer.current = setTimeout(() => {
      triggerEmergency();
      setIsHolding(false);
    }, 3000);
  };

  const handlePressOut = () => {
    if (!activated) {
      setIsHolding(false);
      if (holdTimer.current) clearTimeout(holdTimer.current);
      holdProgress.value = withTiming(0, { duration: 300 });
    }
  };

  const progressStyle = useAnimatedStyle(() => ({
    height: `${holdProgress.value * 100}%`,
  }));

  const resolveEmergency = async () => {
    if (!emergencyId || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await apiService.put<{ status: string }>(`/emergency/resolve/${emergencyId}`, {});
      if (result.error || !result.data) {
        setError(result.error || 'Unable to resolve the emergency. Please retry.');
        return;
      }
    } catch (resolveError) {
      setError(resolveError instanceof Error ? resolveError.message : 'Unable to resolve the emergency.');
      return;
    } finally {
      setSubmitting(false);
    }
    setActivated(false);
    setEmergencyId(null);
    setResponders([]);
    holdProgress.value = 0;
  };

  return (
    <LinearGradient
      colors={activated ? theme.colors.gradients.danger : theme.colors.gradients.primary}
      style={styles.container}
    >
      <StatusBar style="light" />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Ionicons name="close" size={28} color="#FFF" />
          </TouchableOpacity>
          <NavioraText type="h3">EMERGENCY SOS</NavioraText>
          <View style={{ width: 44 }} />
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          {activated ? (
            <Animated.View entering={FadeInDown} style={styles.dispatchView}>
              <View style={styles.alertIconWrapper}>
                <PulseAnimation color="#FFF" size={140}>
                  <View style={styles.alertIcon}>
                    <Ionicons name="notifications" size={64} color={theme.colors.error} />
                  </View>
                </PulseAnimation>
              </View>

              <NavioraText type="h1" align="center" style={styles.alertTitle}>EMERGENCY DISPATCHED</NavioraText>
              <NavioraText type="body" align="center" color="medium" style={styles.alertSubtitle}>
                Emergency #{emergencyId} has been created. Please remain where you are.
              </NavioraText>
              {error ? <NavioraText type="caption" color="danger" style={styles.actionError}>{error}</NavioraText> : null}

              <GlassCard style={styles.locationCard}>
                <View style={styles.locationInfo}>
                  <Ionicons name="location" size={20} color={theme.colors.accent} />
                  <NavioraText type="label" style={{ marginLeft: 8 }}>{locationLabel}</NavioraText>
                </View>
                <NavioraText type="xs" color="low" style={{ marginTop: 4 }}>
                  {locationLabel === 'Location unavailable' ? 'Device location was unavailable for this alert.' : 'Device coordinates were included with this SOS.'}
                </NavioraText>
              </GlassCard>

              <NavioraText type="label" color="medium" style={styles.sectionTitle}>NEARBY RESPONDERS</NavioraText>
              {responders.length > 0 ? (
                responders.map((staff, idx) => (
                  <GlassCard key={String(staff.staff_id || staff.id || staff.user_id || idx)} style={styles.staffCard}>
                    <View style={{ flex: 1, marginLeft: 16 }}>
                      <NavioraText type="h3">{staff.name || staff.full_name || 'Responder'}</NavioraText>
                      <NavioraText type="xs" color="low">
                        {staff.role ? `${String(staff.role).toUpperCase()} · ` : ''}{staff.distance_meters}m away
                      </NavioraText>
                    </View>
                    {staff.estimated_arrival_minutes != null ? <View style={styles.etaBadge}>
                      <NavioraText type="label" color="primary">{staff.estimated_arrival_minutes}m</NavioraText>
                    </View> : null}
                  </GlassCard>
                ))
              ) : <NavioraText type="body" color="low">No responder information is available yet.</NavioraText>}

              <View style={styles.dispatchActions}>
                <TouchableOpacity style={styles.resolveBtn} onPress={() => void resolveEmergency()} disabled={submitting}>
                  {submitting ? <ActivityIndicator color="#fff" /> : <NavioraText type="h3" color="medium">Mark as Resolved</NavioraText>}
                </TouchableOpacity>
              </View>
            </Animated.View>
          ) : (
            <View style={styles.triggerView}>
              <View style={styles.warningBox}>
                <Ionicons name="alert-circle" size={32} color={theme.colors.error} />
                <NavioraText type="h3" style={{ marginTop: 12 }}>Medical Emergency Only</NavioraText>
                <NavioraText type="body" align="center" color="low" style={{ marginTop: 8 }}>
                  Activating this sends an alert to hospital staff. Device location is included only when permission is granted.
                </NavioraText>
              </View>

              <View style={styles.sosContainer}>
                <PulseAnimation color={theme.colors.error} size={300}>
                  <TouchableOpacity
                    activeOpacity={1}
                    onPressIn={handlePressIn}
                    onPressOut={handlePressOut}
                    style={[styles.sosButton, { backgroundColor: 'rgba(255,255,255,0.05)', borderColor: theme.colors.glass.border }]}
                  >
                    <Animated.View style={[styles.progressOverlay, progressStyle, { backgroundColor: theme.colors.error }]} />
                    <Ionicons name="power" size={80} color="#FFF" />
                    <NavioraText type="h1" style={{ color: '#FFF', marginTop: 16 }}>SOS</NavioraText>
                  </TouchableOpacity>
                </PulseAnimation>

                <NavioraText type="label" color="medium" style={styles.holdText}>
                  {submitting ? 'SENDING EMERGENCY ALERT…' : isHolding ? 'HOLDING... RELEASING CANCELS' : 'HOLD FOR 3 SECONDS'}
                </NavioraText>
                {error ? <NavioraText type="caption" color="danger" style={styles.actionError}>{error}</NavioraText> : null}
              </View>

            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20 },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  scrollContent: { paddingHorizontal: 24, paddingBottom: 60 },
  triggerView: { alignItems: 'center', marginTop: 20 },
  warningBox: { alignItems: 'center', marginBottom: 60 },
  sosContainer: { alignItems: 'center', marginBottom: 60 },
  sosButton: { width: 220, height: 220, borderRadius: 110, borderWidth: 2, justifyContent: 'center', alignItems: 'center', overflow: 'hidden' },
  progressOverlay: { position: 'absolute', bottom: 0, left: 0, right: 0 },
  holdText: { marginTop: 32, letterSpacing: 2 },
  contactSection: { width: '100%' },
  contactCard: { flexDirection: 'row', alignItems: 'center', padding: 16 },
  contactInfo: { flex: 1 },
  callBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  dispatchView: { marginTop: 20 },
  alertIconWrapper: { alignItems: 'center', marginBottom: 40 },
  alertIcon: { width: 120, height: 120, borderRadius: 60, backgroundColor: '#FFF', justifyContent: 'center', alignItems: 'center' },
  alertTitle: { marginBottom: 12 },
  alertSubtitle: { marginBottom: 32 },
  locationCard: { padding: 16, alignItems: 'center', marginBottom: 32 },
  locationInfo: { flexDirection: 'row', alignItems: 'center' },
  sectionTitle: { letterSpacing: 1.5, marginBottom: 16, fontWeight: '800' },
  staffCard: { flexDirection: 'row', alignItems: 'center', padding: 16, marginBottom: 12 },
  etaBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.05)' },
  dispatchActions: { marginTop: 40 },
  resolveBtn: { alignSelf: 'center', padding: 12 },
  actionError: { marginTop: 12, textAlign: 'center' },
});
