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
import * as Speech from 'expo-speech';
import { addSpeechRecognitionListener, ExpoSpeechRecognitionModule } from 'expo-speech-recognition';
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

type RequestError = { response?: { status?: number; data?: unknown }; message?: string };
type ScreenStatus = 'idle' | 'recording' | 'processing';

function apiErrorMessage(cause: unknown, fallback: string): string {
  const error = cause as RequestError;
  const data = error.response?.data;
  if (data && typeof data === 'object') {
    const payload = data as { detail?: unknown; message?: unknown; error?: unknown };
    for (const value of [payload.detail, payload.message, payload.error]) {
      if (typeof value === 'string' && value.trim()) return value;
    }
    if (Array.isArray(payload.detail)) {
      const messages = payload.detail.flatMap((item: unknown) => {
        if (!item || typeof item !== 'object') return [];
        const detail = item as { msg?: unknown; loc?: unknown };
        if (typeof detail.msg !== 'string') return [];
        const location = Array.isArray(detail.loc)
          ? detail.loc.filter((part): part is string | number => typeof part === 'string' || typeof part === 'number').filter((part) => part !== 'body').join('.')
          : '';
        return [location ? `${location}: ${detail.msg}` : detail.msg];
      });
      if (messages.length) return messages.join(' ');
    }
  }
  return typeof error.message === 'string' && error.message.trim() ? error.message : fallback;
}

export default function VoiceAssistantScreen() {
  const [permission, setPermission] = useState<boolean | null>(null);
  const [status, setStatus] = useState<ScreenStatus>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [screenError, setScreenError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const recognitionActiveRef = useRef(false);
  const stopRequestedRef = useRef(false);
  const submittedRef = useRef(false);
  const transcriptRef = useRef('');
  const submitTranscriptRef = useRef<(transcript: string) => void>(() => undefined);
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

  useEffect(() => {
    const resultSubscription = addSpeechRecognitionListener('result', (event) => {
      const transcript = event.results[0]?.transcript?.trim();
      if (transcript && event.isFinal) transcriptRef.current = transcript;
    });
    const endSubscription = addSpeechRecognitionListener('end', () => {
      recognitionActiveRef.current = false;
      stopRequestedRef.current = false;
      const transcript = transcriptRef.current.trim();
      if (transcript && !submittedRef.current) {
        submittedRef.current = true;
        submitTranscriptRef.current(transcript);
      } else if (!transcript) {
        setStatus('idle');
      }
    });
    const errorSubscription = addSpeechRecognitionListener('error', (event) => {
      recognitionActiveRef.current = false;
      stopRequestedRef.current = false;
      submittedRef.current = true;
      setStatus('idle');
      console.error('Speech recognition error:', event.error, event.message);
      if (event.error !== 'aborted') {
        if (event.error === 'not-allowed') setPermission(false);
        addErrorMessage(event.error === 'not-allowed'
          ? 'Microphone or speech recognition permission was denied. Open Settings to allow access.'
          : event.error === 'service-not-allowed'
            ? 'No speech recognition service is available. Enable a speech service on this device and try again.'
            : `Speech recognition failed (${event.error}). Please try again.`);
      }
    });
    return () => {
      resultSubscription.remove();
      endSubscription.remove();
      errorSubscription.remove();
      try { ExpoSpeechRecognitionModule.abort(); } catch { /* Native module may be unavailable in preview. */ }
      Speech.stop();
    };
  }, []);

  const addErrorMessage = (message: string) => {
    setMessages((items) => [...items, {
      id: `error-${++nextMessageId.current}`,
      role: 'error',
      text: message,
    }]);
  };

  const submitTranscript = async (transcript: string) => {
    setStatus('processing');
    setScreenError(null);
    try {
      const { data } = await api.patient.processVoiceText(transcript);
      const received = data as VoiceResponse;
      const additions: Message[] = [{ id: `user-${++nextMessageId.current}`, role: 'user', text: received.text || transcript }];
      if (received.response_text) additions.push({
        id: `assistant-${++nextMessageId.current}`,
        role: 'assistant',
        text: received.response_text,
        fallbackUsed: received.fallback_used === true,
      });
      if (additions.length) setMessages((items) => [...items, ...additions]);
      setStatus('idle');
      if (received.response_text) Speech.speak(received.response_text);
    } catch (cause: unknown) {
      const code = (cause as RequestError).response?.status;
      setStatus('idle');
      if (code === 404 || code === 501) {
        setUnavailable(true);
      } else {
        addErrorMessage(apiErrorMessage(cause, 'Something went wrong. Tap to retry.'));
      }
    }
  };
  submitTranscriptRef.current = (transcript) => { void submitTranscript(transcript); };

  const startListening = async () => {
    setScreenError(null);
    try {
      let hasPermission = permission === true;
      if (!hasPermission) {
        const result = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
        hasPermission = result.granted;
        setPermission(hasPermission);
      }
      if (!hasPermission) return;
      if (!ExpoSpeechRecognitionModule.isRecognitionAvailable()) {
        setScreenError('Speech recognition is not available on this device.');
        return;
      }
      transcriptRef.current = '';
      stopRequestedRef.current = false;
      submittedRef.current = false;
      ExpoSpeechRecognitionModule.start({
        lang: 'en-US',
        interimResults: true,
        maxAlternatives: 1,
        continuous: false,
        addsPunctuation: true,
        androidIntentOptions: {
          EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS: 5000,
          EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS: 5000,
        },
      });
      recognitionActiveRef.current = true;
      setStatus('recording');
    } catch (cause: unknown) {
      recognitionActiveRef.current = false;
      setStatus('idle');
      console.error('Speech recognition start failed:', cause);
      setScreenError(cause instanceof Error && cause.message
        ? `Could not start speech recognition: ${cause.message}`
        : 'Could not start speech recognition. Check microphone access and try again.');
    }
  };

  const stopListening = () => {
    if (!recognitionActiveRef.current) return;
    recognitionActiveRef.current = false;
    stopRequestedRef.current = true;
    setStatus('processing');
    try { ExpoSpeechRecognitionModule.stop(); }
    catch {
      stopRequestedRef.current = false;
      setStatus('idle');
      addErrorMessage('Could not stop speech recognition. Please try again.');
    }
  };

  const toggleListening = () => {
    if (status === 'recording') {
      stopListening();
    } else if (status === 'idle') {
      void startListening();
    }
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
            </View>
          )}
        />
      ) : (
        <View style={styles.empty}><EmptyState message="Hold the microphone and speak to request help." /></View>
      )}

      <View style={styles.controls}>
        {status === 'processing' ? <ActivityIndicator size="large" color={colors.primary} style={styles.spinner} /> : null}
        <View style={styles.waveform} accessibilityLabel={status === 'recording' ? 'Listening' : 'Audio waveform'}><View style={[styles.waveBar, status === 'recording' && styles.waveBarActive]} /><View style={[styles.waveBarTall, status === 'recording' && styles.waveBarActive]} /><View style={[styles.waveBar, status === 'recording' && styles.waveBarActive]} /><View style={[styles.waveBarTall, status === 'recording' && styles.waveBarActive]} /><View style={[styles.waveBar, status === 'recording' && styles.waveBarActive]} /><View style={[styles.waveBarTall, status === 'recording' && styles.waveBarActive]} /><View style={[styles.waveBar, status === 'recording' && styles.waveBarActive]} /><View style={[styles.waveBarTall, status === 'recording' && styles.waveBarActive]} /><View style={[styles.waveBar, status === 'recording' && styles.waveBarActive]} /></View>
        <Animated.View style={{ transform: [{ scale: pulse }] }}>
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel={status === 'recording' ? 'Listening. Tap to stop and send.' : 'Tap to start a voice request'}
            disabled={status === 'processing'}
            onPress={toggleListening}
            style={[styles.mic, status === 'recording' && styles.recording]}
          >
            <Ionicons name={status === 'recording' ? 'radio-button-on' : 'mic'} size={30} color={colors.white} />
          </TouchableOpacity>
        </Animated.View>
        <Text style={styles.hint}>
          {status === 'recording' ? 'Listening… tap to stop and send' : status === 'processing' ? 'Processing your request…' : 'Tap to speak'}
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
  waveBarActive: { backgroundColor: colors.danger },
});
