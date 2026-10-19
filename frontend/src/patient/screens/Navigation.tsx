import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Speech from 'expo-speech';
import { api, type Department } from '../../shared/services/api';
import { BackendNotAvailable, Button, Card, EmptyState, ErrorState, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type NavigationStep = string | { instruction?: string; text?: string; description?: string };
type RouteResponse = { steps?: NavigationStep[]; directions?: NavigationStep[] };
type Amenity = { name: string; location: string };
type RequestError = { response?: { status?: number } };

export default function NavigationScreen() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<Department | null>(null);
  const [steps, setSteps] = useState<string[]>([]);
  const [amenities, setAmenities] = useState<Amenity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);

  const loadDepartments = useCallback(async () => {
    setLoading(true); setError(null); setUnavailable(null);
    try { const result = await api.patient.getNavigationDepartments(); setDepartments(Array.isArray(result.data) ? result.data : []); }
    catch (cause: unknown) { const code = (cause as RequestError).response?.status; if (code === 404 || code === 501) setUnavailable('GET /navigation/departments'); else setError('Could not load destinations. Please retry.'); }
    finally { setLoading(false); }
  }, []);

  const loadAmenities = useCallback(async () => {
    try { const result = await api.patient.getNavigationAmenities(); setAmenities(result.data.pois ?? []); }
    catch { /* Optional amenities are shown only when the service responds. */ }
  }, []);

  useEffect(() => { void loadDepartments(); void loadAmenities(); }, [loadDepartments, loadAmenities]);

  const chooseDestination = async (destination: Department) => {
    setSelected(destination); setSteps([]); setError(null); setUnavailable(null); setLoading(true);
    try {
      const result = await api.patient.getNavigationRoute('current', String(destination.id));
      const payload = result.data as RouteResponse;
      const list = payload.steps ?? payload.directions ?? [];
      setSteps(list.map((step) => typeof step === 'string' ? step : step.instruction ?? step.text ?? step.description ?? '').filter(Boolean));
    } catch (cause: unknown) { const code = (cause as RequestError).response?.status; if (code === 404 || code === 501) setUnavailable('GET /navigation/route'); else setError('Could not load directions. Please retry.'); }
    finally { setLoading(false); }
  };

  const filtered = useMemo(() => departments.filter((item) => item.name.toLowerCase().includes(query.trim().toLowerCase())), [departments, query]);
  const speakSteps = () => Speech.speak(steps.map((step, index) => `Step ${index + 1}. ${step}`).join('. '), { language: 'en' });

  return <ScreenContainer>
    <SectionHeader title="Indoor Wayfinding" />
    <Text style={styles.subtitle}>Search hospital destinations and get step-by-step directions</Text>
    {selected ? <TouchableOpacity onPress={() => { setSelected(null); setSteps([]); setUnavailable(null); setError(null); }} style={styles.back}><Ionicons name="arrow-back" size={17} color={colors.primary} /><Text style={styles.backText}>All destinations</Text></TouchableOpacity> : null}
    {!selected ? <View style={styles.searchWrap}><Ionicons name="search-outline" size={19} color={colors.textMuted} /><TextInput value={query} onChangeText={setQuery} placeholder="Search departments" accessibilityLabel="Search destinations" style={styles.search} placeholderTextColor={colors.textMuted} /></View> : null}
    {unavailable ? <BackendNotAvailable endpoint={unavailable} /> : error ? <ErrorState message={error} onRetry={() => selected ? void chooseDestination(selected) : void loadDepartments()} /> : loading ? <Loader message="Loading navigation…" /> : selected ? <ScrollView><Card><Text style={styles.title}>Directions to {selected.name}</Text>{steps.length ? steps.map((step, index) => <View key={`${index}-${step}`} style={styles.step}><View style={styles.stepIcon}><Ionicons name={index === steps.length - 1 ? 'checkmark-circle-outline' : 'arrow-up-outline'} size={17} color={colors.primary} /></View><Text style={styles.instruction}>{step}</Text></View>) : <EmptyState message="No directions are available for this destination." />}<Button title="Voice Guide" onPress={speakSteps} disabled={!steps.length} /></Card></ScrollView> : filtered.length ? <ScrollView>{filtered.map((destination) => <TouchableOpacity key={destination.id} onPress={() => void chooseDestination(destination)}><Card style={styles.destination}><View style={styles.destinationIcon}><Ionicons name="navigate-outline" size={20} color={colors.primary} /></View><View style={styles.destinationCopy}><Text style={styles.title}>{destination.name}</Text>{destination.description ? <Text style={styles.description}>{destination.description}</Text> : null}<Text style={styles.link}>Get directions <Ionicons name="arrow-forward" size={13} color={colors.primary} /></Text></View></Card></TouchableOpacity>)}</ScrollView> : <EmptyState message={departments.length ? 'No destinations match your search.' : 'No destinations are available.'} />}
    {!selected && amenities.length ? <View style={styles.amenities}><Text style={styles.title}>Nearby amenities · Restrooms</Text>{amenities.map((item, index) => <Text key={`${item.name}-${index}`} style={styles.amenity}>{item.name} · {item.location}</Text>)}</View> : null}
  </ScreenContainer>;
}

const styles = StyleSheet.create({ subtitle: { color: colors.textMuted, marginTop: -7, marginBottom: 14 }, searchWrap: { flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1, borderColor: colors.border, borderRadius: 14, paddingHorizontal: 12, marginBottom: 12, backgroundColor: colors.white }, search: { flex: 1, paddingVertical: 12, color: colors.text }, destination: { marginBottom: 10, flexDirection: 'row', alignItems: 'center', gap: 12 }, destinationIcon: { width: 42, height: 42, borderRadius: 14, backgroundColor: colors.primaryLight, alignItems: 'center', justifyContent: 'center' }, destinationCopy: { flex: 1 }, title: { color: colors.text, fontWeight: '700', fontSize: 16 }, description: { color: colors.textMuted, marginTop: 6 }, link: { color: colors.primary, fontWeight: '700', marginTop: 10 }, back: { flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 12 }, backText: { color: colors.primary, fontWeight: '700' }, step: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, paddingVertical: 12, borderBottomWidth: 1, borderColor: colors.border }, stepIcon: { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.primaryLight, alignItems: 'center', justifyContent: 'center' }, instruction: { color: colors.text, flex: 1, lineHeight: 20, paddingTop: 4 }, amenities: { paddingTop: 14 }, amenity: { color: colors.textMuted, paddingTop: 7 } });
