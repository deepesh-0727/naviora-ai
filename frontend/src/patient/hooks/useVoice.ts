import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../shared/services/api';
import { websocketClient } from '../../shared/services/websocket';

export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  audioB64?: string | null;
}

export type VoiceStatus = 'idle' | 'recording' | 'processing' | 'error';

export interface VoiceState {
  status: VoiceStatus;
  messages: ConversationMessage[];
  error: string | null;
  backendUnavailable: boolean;
  sendAudio: (audioUri: string, mimeType?: string) => Promise<void>;
  clearMessages: () => void;
}

export function useVoice(): VoiceState {
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);
  const msgCounter = useRef(0);

  const nextId = () => {
    msgCounter.current += 1;
    return String(msgCounter.current);
  };

  const sendAudio = useCallback(async (audioUri: string, mimeType = 'audio/m4a') => {
    setStatus('processing');
    setError(null);
    setBackendUnavailable(false);

    // Append a placeholder user message
    const userMsgId = nextId();
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: 'user', text: '🎙 Audio message sent…' },
    ]);

    try {
      const form = new FormData();
      // React Native FormData accepts { uri, name, type }
      form.append('audio', { uri: audioUri, name: 'audio.m4a', type: mimeType } as unknown as Blob);

      const res = await api.patient.processVoice(form);
      const { query, response_text, audio_response_b64 } = res.data;

      // Replace user placeholder with real transcript
      setMessages((prev) =>
        prev.map((m) =>
          m.id === userMsgId ? { ...m, text: query || 'Audio message sent' } : m,
        ),
      );

      // Append assistant reply
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: 'assistant',
          text: response_text,
          audioB64: audio_response_b64,
        },
      ]);
      setStatus('idle');
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status === 404 || status === 501) {
        setBackendUnavailable(true);
        setStatus('idle');
        // Remove the pending user message
        setMessages((prev) => prev.filter((m) => m.id !== userMsgId));
      } else {
        setError('Voice processing failed. Please try again.');
        setStatus('error');
      }
    }
  }, []);

  useEffect(() => {
    void websocketClient.connect();
    const unsub = websocketClient.subscribe('voice_result', (payload: unknown) => {
      const p = payload as { response_text?: string; query?: string };
      if (p?.response_text) {
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: 'assistant', text: p.response_text! },
        ]);
      }
    });
    return () => {
      unsub();
    };
  }, []);

  return {
    status,
    messages,
    error,
    backendUnavailable,
    sendAudio,
    clearMessages: () => setMessages([]),
  };
}
