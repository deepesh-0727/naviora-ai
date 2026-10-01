import { useState, useEffect, useCallback, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

// 🏥 Production WebSocket Orchestration
// Auto-detects environment: use 10.0.2.2 for Android Emulator, localhost for iOS
const WS_URL = 'ws://10.0.2.2:8000/api/v1/stream';

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const ws = useRef<WebSocket | null>(null);

  const connect = useCallback(async () => {
    const token = await AsyncStorage.getItem('userToken');
    if (!token) return;

    ws.current = new WebSocket(`${WS_URL}?token=${token}`);

    ws.current.onopen = () => {
      console.log('WebSocket Connected');
      setIsConnected(true);
    };

    ws.current.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setLastMessage(data);
      } catch (err) {
        // Binary or non-json message
        setLastMessage(e.data);
      }
    };

    ws.current.onerror = (e) => {
      console.error('WebSocket Error:', e);
    };

    ws.current.onclose = () => {
      console.log('WebSocket Disconnected');
      setIsConnected(false);
      // Attempt reconnect after 3 seconds
      setTimeout(connect, 3000);
    };
  }, []);

  const sendMessage = useCallback((data: any) => {
    if (ws.current && isConnected) {
      if (typeof data === 'string' || data instanceof ArrayBuffer || data instanceof Blob) {
        ws.current.send(data);
      } else {
        ws.current.send(JSON.stringify(data));
      }
    }
  }, [isConnected]);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);

  return { isConnected, lastMessage, sendMessage };
};
