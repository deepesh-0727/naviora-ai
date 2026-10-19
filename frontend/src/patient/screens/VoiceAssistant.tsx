import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  FlatList,
  Linking,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../shared/services/api';
import {
  BackendNotAvailable,
  Badge,
  Button,
  Card,
  EmptyState,
  ScreenContainer,
  SectionHeader,
} from '../../shared/components';
import { colors } from '../../shared/theme/colors';

type VoiceResponse = {
  text?: string;
  intent?: string;
  entities?: Record<string, unknown>;
  response_text?: string;
  response_audio_url?: string | null;
  fallback_used?: boolean;
  fallback_reason?: string | null;
};

type Message = {
  id: string;
  role: 'user' | 'assistant' | 'error';
  text: string;
  fallbackUsed?: boolean;
};

type RequestError = { response?: { status?: number } };
type ScreenStatus = 'idle' | 'recording' | 'processing';

export default function VoiceAssistantScreen() {
  const [permission, setPermission] = useState<boolean | null>(null);
  const [status, setStatus] = useState<ScreenStatus>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [lastRecordingUri, setLastRecordingUri] = useState<string | null>(null);
  const [screenError, setScreenError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const pressedRef = useRef(false);
  const soundRef = useRef<Audio.Sound | null>(null);
  const listRef = useRef<FlatList<Message>>(null);
  const nextMessageId = useRef(0);
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (status !== 'recording') {
      pulse.stopAnimation();
      pulse.setValue(1);
      return undefined;
    }

    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.12, duration: 500, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 500, useNativeDriver: true }),
      ]),
    );
    animation.start();
    return () => animation.stop();
  }, [pulse, status]);

  useEffect(() => {
    if (messages.length) listRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  useEffect(() => () => {
    const activeRecording = recordingRef.current;
    recordingRef.current = null;
    if (activeRecording) void activeRecording.stopAndUnloadAsync().catch(() => undefined);
    if (soundRef.current) void soundRef.current.unloadAsync().catch(() => undefined);
  }, []);

  const addErrorMessage = (message: string) => {
    setMessages((items) => [...items, {
      id: `error-${++nextMessageId.current}`,
      role: 'error',
      text: message,
    }]);
  };

  const playResponse = async (url?: string | null) => {
    if (!url) return;
    try {
      if (soundRef.current) await soundRef.current.unloadAsync();
      const playback = await Audio.Sound.createAsync({ uri: url }, { shouldPlay: true });
      soundRef.current = playback.sound;
    } catch {
      setScreenError('The response was received, but its audio could not be played.');
    }
  };

  const uploadRecording = async (uri: string) => {
    setStatus('processing');
    setScreenError(null);
    try {
      const form = new FormData();
      const extension = uri.split('?')[0].split('.').pop()?.toLowerCase() ?? 'm4a';
      const audioType = extension === 'webm'
        ? 'audio/webm'
        : extension === '3gp'
          ? 'audio/3gpp'
          : extension === 'wav'
            ? 'audio/wav'
            : 'audio/m4a';
      form.append('audio', {
        uri,
        name: `voice.${extension}`,
        type: audioType,
      } as unknown as Blob);

      const { data } = await api.patient.processVoice(form);
      const received = data as VoiceResponse;
      const additions: Message[] = [];
      if (received.text) {
        additions.push({
          id: `user-${++nextMessageId.current}`,
          role: 'user',
          text: received.text,
        });
      }
      if (received.response_text) {
        additions.push({
          id: `assistant-${++nextMessageId.current}`,
          role: 'assistant',
          text: received.response_text,
          fallbackUsed: received.fallback_used === true,
        });
      }
      if (additions.length) setMessages((items) => [...items, ...additions]);
      setStatus('idle');
      await playResponse(received.response_audio_url);
    } catch (cause: unknown) {
      const code = (cause as RequestError).response?.status;
      setStatus('idle');
      if (code === 404 || code === 501) {
        setUnavailable(true);
      } else {
        addErrorMessage('Something went wrong. Tap to retry.');
      }
    }
  };

  const startRecording = async () => {
    setScreenError(null);
    try {
      let hasPermission = permission === true;
      if (!hasPermission) {
        const result = await Audio.requestPermissionsAsync();
        hasPermission = result.status === 'granted';
        setPermission(hasPermission);
      }
      if (!hasPermission) return;

      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const result = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      recordingRef.current = result.recording;
      setStatus('recording');
      if (!pressedRef.current) void stopRecording(result.recording);
    } catch {
      setStatus('idle');
      setScreenError('Could not start recording. Check microphone access and try again.');
    }
  };

  const stopRecording = async (recording = recordingRef.current) => {
    if (!recording || status === 'processing') return;
    recordingRef.current = null;
    setStatus('processing');
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      if (!uri) throw new Error('Recording file is unavailable');
      setLastRecordingUri(uri);
      await uploadRecording(uri);
    } catch {
      setStatus('idle');
      addErrorMessage('Something went wrong. Tap to retry.');
    }
  };

  const retryLastRecording = () => {
    if (lastRecordingUri) void uploadRecording(lastRecordingUri);
  };

  const handlePressIn = () => {
    if (status !== 'idle') return;
    pressedRef.current = true;
    void startRecording();
  };

  const handlePressOut = () => {
    pressedRef.current = false;
    if (recordingRef.current) void stopRecording(recordingRef.current);
  };

  if (unavailable) {
    return <ScreenContainer><SectionHeader title="Voice Assistant" /><BackendNotAvailable endpoint="POST /api/v1/voice/process" /></ScreenContainer>;
  }

  if (permission === false) {
    return (
      <ScreenContainer>
        <SectionHeader title="Voice Assistant" />
        <Card style={styles.permissionCard}>
          <Text style={styles.title}>Microphone access required</Text>
          <Text style={styles.copy}>Microphone access required. Open Settings to enable.</Text>
          <Button
            title="Open Settings"
            onPress={() => Platform.OS === 'ios' ? void Linking.openURL('app-settings:') : void Linking.openSettings()}
          />
        </Card>
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer style={styles.screen}>
      <View style={styles.voiceHeader}><View style={styles.voiceHeading}><SectionHeader title="Naviora Voice AI" /><Text style={styles.voiceSubtitle}>Hospital triage and wayfinding</Text></View><Badge label="Live Agent" /></View>
      <View style={styles.suggestions}><Text style={styles.suggestion}>Check my queue</Text><Text style={styles.suggestion}>Book an appointment</Text><Text style={styles.suggestion}>Find a department</Text></View>
      {screenError ? <Text accessibilityRole="alert" style={styles.screenError}>{screenError}</Text> : null}
      {messages.length ? (
        <FlatList
          ref={listRef}
          style={styles.conversation}
          contentContainerStyle={styles.conversationContent}
          data={messages}
          keyExtractor={(item) => item.id}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
          renderItem={({ item }) => (
            <View style={[
              styles.bubble,
              item.role === 'user' ? styles.userBubble : item.role === 'error' ? styles.errorBubble : styles.agentBubble,
            ]}>
              {item.fallbackUsed ? <Badge label="Rule mode" color={colors.textMuted} /> : null}
              <Text style={item.role === 'user' ? styles.userText : item.role === 'error' ? styles.errorText : styles.agentText}>
                {item.text}
              </Text>
              {item.role === 'error' && lastRecordingUri
                ? <Button title="Retry" variant="secondary" onPress={retryLastRecording} style={styles.retryButton} />
                : null}
            </View>
          )}
        />
      ) : (
        <View style={styles.empty}><EmptyState message="Hold the microphone and speak to request help." /></View>
      )}

      <View style={styles.controls}>
        {status === 'processing' ? <ActivityIndicator size="large" color={colors.primary} style={styles.spinner} /> : null}
        <View style={styles.waveform} accessibilityLabel="Audio waveform"><View style={styles.waveBar} /><View style={styles.waveBarTall} /><View style={styles.waveBar} /><View style={styles.waveBarTall} /><View style={styles.waveBar} /><View style={styles.waveBarTall} /><View style={styles.waveBar} /><View style={styles.waveBarTall} /><View style={styles.waveBar} /></View>
        <Animated.View style={{ transform: [{ scale: pulse }] }}>
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel={status === 'recording' ? 'Recording. Release to send.' : 'Hold to record a voice request'}
            disabled={status === 'processing'}
            onPressIn={handlePressIn}
            onPressOut={handlePressOut}
            style={[styles.mic, status === 'recording' && styles.recording]}
          >
            <Ionicons name={status === 'recording' ? 'radio-button-on' : 'mic'} size={30} color={colors.white} />
          </TouchableOpacity>
        </Animated.View>
        <Text style={styles.hint}>
          {status === 'recording' ? 'Recording… release to send' : status === 'processing' ? 'Uploading and processing…' : 'Hold to speak'}
        </Text>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  empty: { flex: 1 },
  conversation: { flex: 1 },
  conversationContent: { paddingBottom: 12 },
  permissionCard: { alignItems: 'center' },
  title: { fontSize: 18, fontWeight: '700', color: colors.text },
  copy: { color: colors.textMuted, marginVertical: 12, textAlign: 'center' },
  screenError: { color: colors.danger, textAlign: 'center', marginBottom: 8 },
  bubble: { maxWidth: '84%', padding: 12, borderRadius: 14, marginVertical: 5 },
  userBubble: { alignSelf: 'flex-end', backgroundColor: colors.primary },
  agentBubble: { alignSelf: 'flex-start', backgroundColor: colors.white },
  errorBubble: { alignSelf: 'flex-start', backgroundColor: colors.dangerLight, borderColor: colors.danger, borderWidth: 1 },
  userText: { color: colors.white },
  agentText: { color: colors.text },
  errorText: { color: colors.danger },
  retryButton: { marginTop: 10 },
  controls: { alignItems: 'center', paddingBottom: 8, paddingTop: 12 },
  spinner: { marginBottom: 10 },
  mic: { width: 76, height: 76, borderRadius: 38, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primary },
  recording: { backgroundColor: colors.danger },
  micText: { color: colors.white, fontWeight: '700', fontSize: 24 },
  hint: { textAlign: 'center', color: colors.textMuted, padding: 8 },
  voiceHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  voiceHeading: { flex: 1 },
  voiceSubtitle: { color: colors.textMuted, marginTop: -4 },
  suggestions: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  suggestion: { color: colors.primary, fontSize: 12, fontWeight: '600', backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border, borderRadius: 999, paddingHorizontal: 11, paddingVertical: 8, overflow: 'hidden' },
  waveform: { flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 12 },
  waveBar: { height: 10, width: 4, borderRadius: 2, backgroundColor: colors.primary },
  waveBarTall: { height: 17, width: 4, borderRadius: 2, backgroundColor: colors.primary },
});
