import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, View, TouchableOpacity, ScrollView, SafeAreaView, Dimensions } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeIn, FadeInUp, useAnimatedStyle, useSharedValue, withRepeat, withTiming, withSequence } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAlert } from '../context/AlertContext';
import { NavioraText, GlassCard, PulseAnimation } from '../components/common/AtomicComponents';

const { width } = Dimensions.get('window');

export default function VoiceAssistantScreen({ navigation }: any) {
  const theme = useTheme();
  const { showAlert } = useAlert();
  const { isConnected, lastMessage, sendMessage } = useWebSocket();

  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [status, setStatus] = useState('IDLE');
  const [transcript, setTranscript] = useState('');
  const [aiResponse, setAiResponse] = useState('');

  // Waveform animations
  const barValues = useRef([...Array(12)].map(() => useSharedValue(10))).current;

  useEffect(() => {
    if (status === 'LISTENING') {
      barValues.forEach((val) => {
        val.value = withRepeat(
          withSequence(
            withTiming(20 + Math.random() * 60, { duration: 200 }),
            withTiming(10, { duration: 200 })
          ),
          -1,
          true
        );
      });
    } else {
      barValues.forEach((val) => (val.value = withTiming(10)));
    }
  }, [status]);

  useEffect(() => {
    if (lastMessage?.type === 'voice_response') {
      setStatus('RESPONDING');
      setTranscript(lastMessage.query);
      setAiResponse(lastMessage.response_text);
    }
  }, [lastMessage]);

  async function startRecording() {
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      setRecording(recording);
      setStatus('LISTENING');
      setTranscript('');
      setAiResponse('');
    } catch (err) {
      showAlert('Failed to start audio recording', 'error');
    }
  }

  async function stopRecording() {
    if (!recording) return;
    setStatus('PROCESSING');
    setRecording(null);
    await recording.stopAndUnloadAsync();
    const uri = recording.getURI();
    if (uri) {
      const base64Audio = await FileSystem.readAsStringAsync(uri, { encoding: FileSystem.EncodingType.Base64 });
      sendMessage({ action: 'process_voice', audio: base64Audio });
    }
  }

  const WaveBar = ({ index }: { index: number }) => {
    const animatedStyle = useAnimatedStyle(() => ({
      height: barValues[index].value,
    }));
    return <Animated.View style={[styles.waveBar, animatedStyle, { backgroundColor: theme.colors.primary }]} />;
  };

  const Chip = ({ label, icon }: { label: string; icon: any }) => (
    <TouchableOpacity style={[styles.chip, { backgroundColor: theme.colors.glass.bg, borderColor: theme.colors.glass.border }]}>
      <Ionicons name={icon} size={16} color={theme.colors.primary} />
      <NavioraText type="label" style={{ marginLeft: 8 }}>{label}</NavioraText>
    </TouchableOpacity>
  );

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Ionicons name="close" size={28} color="#FFF" />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <NavioraText type="h3">Voice Assistant</NavioraText>
            <View style={styles.statusRow}>
              <View style={[styles.statusDot, { backgroundColor: isConnected ? theme.colors.status.live : theme.colors.error }]} />
              <NavioraText type="xs" color="low">{isConnected ? 'ONLINE' : 'OFFLINE'}</NavioraText>
            </View>
          </View>
          <TouchableOpacity style={styles.backBtn}>
            <Ionicons name="volume-medium-outline" size={24} color="#FFF" />
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={styles.chatArea} showsVerticalScrollIndicator={false}>
          {transcript ? (
            <Animated.View entering={FadeInUp} style={styles.userBubbleWrapper}>
              <LinearGradient colors={theme.colors.gradients.primary} style={styles.userBubble}>
                <NavioraText type="body">{transcript}</NavioraText>
              </LinearGradient>
            </Animated.View>
          ) : (
            <View style={styles.emptyContainer}>
              <NavioraText type="h2" align="center" color="medium">How can I help you today?</NavioraText>
              <View style={styles.chipRow}>
                <Chip label="Book Appointment" icon="calendar" />
                <Chip label="Check Queue" icon="people" />
                <Chip label="Emergency" icon="alert-circle" />
              </View>
            </View>
          )}

          {aiResponse ? (
            <Animated.View entering={FadeInUp} style={styles.aiBubbleWrapper}>
              <GlassCard style={styles.aiBubble}>
                <View style={styles.aiHeader}>
                  <Ionicons name="sparkles" size={18} color={theme.colors.primary} />
                  <NavioraText type="label" color="primary" style={{ marginLeft: 8 }}>NAVIORA AI</NavioraText>
                </View>
                <NavioraText type="body" style={{ lineHeight: 24 }}>{aiResponse}</NavioraText>
              </GlassCard>
            </Animated.View>
          ) : null}
        </ScrollView>

        <View style={styles.footer}>
          <View style={styles.waveform}>
            {[...Array(12)].map((_, i) => <WaveBar key={i} index={i} />)}
          </View>

          <NavioraText type="label" color="low" style={styles.statusText}>
            {status === 'LISTENING' ? 'LISTENING...' : status === 'PROCESSING' ? 'PROCESSING...' : status === 'RESPONDING' ? 'SPEAKING...' : 'READY'}
          </NavioraText>

          <PulseAnimation color={status === 'LISTENING' ? theme.colors.error : theme.colors.primary} size={status === 'LISTENING' ? 140 : 100}>
            <TouchableOpacity
              onPress={status === 'LISTENING' ? stopRecording : startRecording}
              style={[
                styles.micBtn,
                { backgroundColor: status === 'LISTENING' ? theme.colors.error : theme.colors.primary }
              ]}
            >
              <Ionicons name={status === 'LISTENING' ? "stop" : "mic"} size={42} color="#FFF" />
            </TouchableOpacity>
          </PulseAnimation>

          <NavioraText type="xs" color="low" style={{ marginTop: 20 }}>
            {status === 'LISTENING' ? 'TAP TO STOP' : 'TAP TO SPEAK'}
          </NavioraText>
        </View>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20 },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  headerInfo: { alignItems: 'center' },
  statusRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
  chatArea: { padding: 24, flexGrow: 1, justifyContent: 'center' },
  emptyContainer: { alignItems: 'center' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 10, marginTop: 24 },
  chip: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 20, borderWidth: 1 },
  userBubbleWrapper: { alignItems: 'flex-end', marginBottom: 24 },
  userBubble: { padding: 16, borderRadius: 20, borderBottomRightRadius: 4, maxWidth: '85%' },
  aiBubbleWrapper: { alignItems: 'flex-start', marginBottom: 24 },
  aiBubble: { padding: 16, borderRadius: 20, borderBottomLeftRadius: 4, maxWidth: '85%' },
  aiHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  footer: { alignItems: 'center', paddingBottom: 60, paddingTop: 20 },
  waveform: { flexDirection: 'row', alignItems: 'center', height: 80, marginBottom: 20 },
  waveBar: { width: 6, marginHorizontal: 3, borderRadius: 3 },
  statusText: { letterSpacing: 2, marginBottom: 24 },
  micBtn: { width: 80, height: 80, borderRadius: 40, justifyContent: 'center', alignItems: 'center', elevation: 10, shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 10 },
});
