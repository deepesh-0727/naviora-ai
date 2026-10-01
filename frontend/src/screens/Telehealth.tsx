import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, View, TouchableOpacity, SafeAreaView, ActivityIndicator } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { RTCPeerConnection, RTCView, mediaDevices, RTCSessionDescription, RTCIceCandidate } from 'react-native-webrtc';

import { useTheme } from '../context/ThemeContext';
import { NavioraText } from '../components/common/AtomicComponents';
import { wsClient } from '../services/websocket';

export default function TelehealthScreen({ navigation }: any) {
  const theme = useTheme();
  const [callState, setCallState] = useState<'connecting' | 'connected' | 'ended'>('connecting');
  const [localStream, setLocalStream] = useState<any>(null);
  const [remoteStream, setRemoteStream] = useState<any>(null);
  
  const peerConnection = useRef<RTCPeerConnection | null>(null);

  useEffect(() => {
    // 1. Initialize WebRTC
    const initWebRTC = async () => {
      // Create Peer Connection
      const configuration = {
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' },
        ],
      };
      
      peerConnection.current = new RTCPeerConnection(configuration);
      const pc: any = peerConnection.current;

      // Handle remote stream
      pc.onaddstream = (event: any) => {
        setRemoteStream(event.stream);
        setCallState('connected');
      };

      // ICE candidate handling
      peerConnection.current.onicecandidate = (event: any) => {
        if (event.candidate) {
          wsClient.send('rtc_candidate', { candidate: event.candidate });
        }
      };

      try {
        // Get local media
        const stream = await mediaDevices.getUserMedia({
          audio: true,
          video: {
            width: 640,
            height: 480,
            frameRate: 30,
            facingMode: 'user'
          }
        });
        
        setLocalStream(stream);
        (peerConnection.current as any).addStream(stream);
        
        // Start signaling by sending an offer
        const offer = await peerConnection.current.createOffer();
        await peerConnection.current.setLocalDescription(offer);
        wsClient.send('rtc_offer', { offer });
        
      } catch (err) {
        console.error('Failed to access media devices.', err);
      }
    };

    initWebRTC();

    // 2. Set up signaling subscriptions
    const unsubOffer = wsClient.subscribe('rtc_offer', async (data) => {
      if (peerConnection.current) {
        await peerConnection.current.setRemoteDescription(new RTCSessionDescription(data.offer));
        const answer = await peerConnection.current.createAnswer();
        await peerConnection.current.setLocalDescription(answer);
        wsClient.send('rtc_answer', { answer });
      }
    });

    const unsubAnswer = wsClient.subscribe('rtc_answer', async (data) => {
      if (peerConnection.current) {
        await peerConnection.current.setRemoteDescription(new RTCSessionDescription(data.answer));
      }
    });

    const unsubCandidate = wsClient.subscribe('rtc_candidate', async (data) => {
      if (peerConnection.current && data.candidate) {
        await peerConnection.current.addIceCandidate(new RTCIceCandidate(data.candidate));
      }
    });

    return () => {
      unsubOffer();
      unsubAnswer();
      unsubCandidate();
      
      // Cleanup WebRTC
      if (localStream) {
        localStream.getTracks().forEach((track: any) => track.stop());
      }
      if (peerConnection.current) {
        peerConnection.current.close();
      }
    };
  }, []);

  const endCall = () => {
    setCallState('ended');
    if (localStream) {
      localStream.getTracks().forEach((track: any) => track.stop());
    }
    if (peerConnection.current) {
      peerConnection.current.close();
    }
    navigation.goBack();
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <StatusBar style="light" />

      {/* Remote Viewport */}
      <View style={[styles.remoteViewport, { backgroundColor: theme.colors.surfaceVariant }]}>
        {callState === 'connecting' ? (
          <View style={styles.connectingBox}>
            <ActivityIndicator size="large" color={theme.colors.primary} />
            <NavioraText type="h3" style={{ marginTop: 24 }}>Securing Clinical Line...</NavioraText>
          </View>
        ) : remoteStream ? (
          <RTCView 
            streamURL={remoteStream.toURL()} 
            style={styles.fullScreenVideo} 
            objectFit="cover"
          />
        ) : (
          <View style={styles.videoContent}>
            <View style={[styles.drAvatar, { backgroundColor: theme.colors.primary + '20' }]}>
              <Ionicons name="person" size={120} color={theme.colors.primary} />
            </View>
            <NavioraText type="h1">Dr. Abhay Sharma</NavioraText>
            <NavioraText color="medium">Call {callState}</NavioraText>
          </View>
        )}
      </View>

      {/* Local Viewport (Self) */}
      <View style={[styles.localViewport, { backgroundColor: theme.colors.surface, borderColor: theme.colors.primary }]}>
        {localStream ? (
          <RTCView 
            streamURL={localStream.toURL()} 
            style={styles.localVideo} 
            objectFit="cover"
          />
        ) : (
          <Ionicons name="person-circle" size={48} color={theme.colors.text.low} />
        )}
      </View>

      {/* Header Overlay */}
      <SafeAreaView style={styles.headerOverlay}>
        <TouchableOpacity
          onPress={endCall}
          style={[styles.headerBtn, { backgroundColor: 'rgba(0,0,0,0.5)' }]}
        >
          <Ionicons name="chevron-back" size={24} color="#FFF" />
        </TouchableOpacity>
        <View style={[styles.encryptionBadge, { backgroundColor: 'rgba(16, 185, 129, 0.2)' }]}>
          <Ionicons name="lock-closed" size={14} color={theme.colors.status.active} />
          <NavioraText type="label" style={{ color: theme.colors.status.active, marginLeft: 6 }}>ENCRYPTED</NavioraText>
        </View>
      </SafeAreaView>

      {/* Call Orchestration Controls */}
      <View style={[styles.controls, { backgroundColor: theme.colors.surface }]}>
        <View style={styles.controlRow}>
          <TouchableOpacity style={[styles.roundBtn, { backgroundColor: theme.colors.surfaceVariant }]}>
            <Ionicons name="mic" size={24} color={theme.colors.text.high} />
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.roundBtn, styles.endCallBtn, { backgroundColor: theme.colors.error }]}
            onPress={endCall}
          >
            <Ionicons name="call" size={32} color="#FFF" style={{ transform: [{ rotate: '135deg' }] }} />
          </TouchableOpacity>

          <TouchableOpacity style={[styles.roundBtn, { backgroundColor: theme.colors.surfaceVariant }]}>
            <Ionicons name="videocam" size={24} color={theme.colors.text.high} />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  remoteViewport: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  fullScreenVideo: { width: '100%', height: '100%' },
  connectingBox: { alignItems: 'center' },
  videoContent: { alignItems: 'center' },
  drAvatar: { width: 200, height: 200, borderRadius: 100, justifyContent: 'center', alignItems: 'center', marginBottom: 32 },
  localViewport: {
    position: 'absolute',
    top: 100,
    right: 24,
    width: 110,
    height: 160,
    borderRadius: 20,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
    elevation: 10,
    overflow: 'hidden'
  },
  localVideo: { width: '100%', height: '100%' },
  headerOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 12,
  },
  headerBtn: { width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center' },
  encryptionBadge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  controls: {
    paddingBottom: 50,
    paddingTop: 30,
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 15,
  },
  controlRow: { flexDirection: 'row', justifyContent: 'space-evenly', alignItems: 'center' },
  roundBtn: { width: 64, height: 64, borderRadius: 32, justifyContent: 'center', alignItems: 'center' },
  endCallBtn: { width: 80, height: 80, borderRadius: 40 },
});
