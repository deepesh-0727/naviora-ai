import React, { useEffect, useRef, useState } from 'react';
import { Audio } from 'expo-av';
import { FlatList, Linking, Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { api } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';
import { BackendNotAvailable, Card, EmptyState, ErrorState, ScreenContainer, SectionHeader } from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type VoiceResponse = { text?: string; intent?: string; entities?: Record<string, unknown>; response_text?: string; response_audio_url?: string | null };
type Message = { id: string; role: 'user' | 'assistant'; text: string };
type RequestError = { response?: { status?: number } };

export default function VoiceAssistantScreen() {
  const [permission, setPermission] = useState<boolean | null>(null);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [status, setStatus] = useState<'idle' | 'recording' | 'processing'>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const sound = useRef<Audio.Sound | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    void Audio.requestPermissionsAsync().then(({ status: result }) => setPermission(result === 'granted')).catch(() => setPermission(false));
    void websocketClient.connect();
    const unsubscribe = websocketClient.subscribe('voice_result', (value: unknown) => {
      if (typeof value !== 'object' || value === null) return;
      const result = value as VoiceResponse;
      if (result.response_text) setMessages((items) => [...items, { id: `ws-${Date.now()}`, role: 'assistant', text: result.response_text! }]);
    });
    return () => {
      unsubscribe();
      if (recording) void recording.stopAndUnloadAsync().catch(() => undefined);
      if (sound.current) void sound.current.unloadAsync().catch(() => undefined);
    };
  }, []);

  const startRecording = async () => {
    setError(null);
    try {
      if (permission !== true) {
        const result = await Audio.requestPermissionsAsync();
        setPermission(result.status === 'granted');
        if (result.status !== 'granted') return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const result = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      setRecording(result.recording);
      setStatus('recording');
    } catch {
      setError('Could not start recording. Check microphone access and try again.');
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    setStatus('processing');
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      if (!uri) throw new Error('Recording file is unavailable');
      const form = new FormData();
      form.append('audio', { uri, name: 'voice-command.m4a', type: 'audio/m4a' } as unknown as Blob);
      const result = await api.patient.processVoice(form);
      const data = result.data;
      setMessages((items) => [...items, ...(data.text ? [{ id: `u-${++requestId.current}`, role: 'user' as const, text: data.text }] : []), ...(data.response_text ? [{ id: `a-${++requestId.current}`, role: 'assistant' as const, text: data.response_text }] : [])]);
      if (data.response_audio_url) {
        if (sound.current) await sound.current.unloadAsync();
        const played = await Audio.Sound.createAsync({ uri: data.response_audio_url }, { shouldPlay: true });
        sound.current = played.sound;
      }
      setStatus('idle');
    } catch (cause: unknown) {
      const code = (cause as RequestError).response?.status;
      if (code === 404 || code === 501) setUnavailable(true);
      else setError('Voice processing failed. Please try again.');
      setStatus('idle');
    }
  };

  if (permission === false) return <ScreenContainer><SectionHeader title="Voice Assistant" /><Card style={styles.center}><Text style={styles.title}>Microphone access required</Text><Text style={styles.copy}>Allow microphone access to use voice commands.</Text><TouchableOpacity onPress={() => Platform.OS === 'ios' ? void Linking.openURL('app-settings:') : void Linking.openSettings()}><Text style={styles.link}>Open Settings</Text></TouchableOpacity></Card></ScreenContainer>;
  if (unavailable) return <ScreenContainer><SectionHeader title="Voice Assistant" /><BackendNotAvailable endpoint="POST /voice/process" /></ScreenContainer>;

  return <ScreenContainer style={styles.screen}>
    <SectionHeader title="Voice Assistant" />
    {error ? <ErrorState message={error} onRetry={() => setError(null)} /> : null}
    {messages.length ? <FlatList data={messages} keyExtractor={(item) => item.id} renderItem={({ item }) => <View style={[styles.bubble, item.role === 'user' ? styles.user : styles.agent]}><Text style={item.role === 'user' ? styles.userText : styles.agentText}>{item.text}</Text></View>} /> : <EmptyState message="Speak to ask a question or request help." />}
    <TouchableOpacity accessibilityRole="button" accessibilityLabel={status === 'recording' ? 'Stop recording' : 'Start recording'} disabled={status === 'processing' || permission === null} onPress={() => void (status === 'recording' ? stopRecording() : startRecording())} style={[styles.mic, status === 'recording' && styles.recording]}><Text style={styles.micText}>{status === 'recording' ? 'Stop' : status === 'processing' ? '…' : '🎙'}</Text></TouchableOpacity>
    <Text style={styles.hint}>{status === 'recording' ? 'Listening · tap to finish' : status === 'processing' ? 'Processing…' : 'Tap to speak'}</Text>
  </ScreenContainer>;
}

const styles = StyleSheet.create({ screen: { flex: 1 }, center: { alignItems: 'center' }, title: { fontSize: 18, fontWeight: '700', color: colors.text }, copy: { color: colors.textMuted, marginVertical: 12, textAlign: 'center' }, link: { color: colors.primary, fontWeight: '700', padding: 12 }, bubble: { maxWidth: '82%', padding: 12, borderRadius: 14, marginVertical: 5 }, user: { alignSelf: 'flex-end', backgroundColor: colors.primary }, agent: { alignSelf: 'flex-start', backgroundColor: colors.white }, userText: { color: '#fff' }, agentText: { color: colors.text }, mic: { alignSelf: 'center', width: 72, height: 72, borderRadius: 36, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primary, marginTop: 12 }, recording: { backgroundColor: colors.danger }, micText: { color: '#fff', fontWeight: '700', fontSize: 18 }, hint: { textAlign: 'center', color: colors.textMuted, padding: 8 } });
