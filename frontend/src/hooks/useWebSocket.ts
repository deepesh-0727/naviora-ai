import { useState, useEffect, useCallback, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { CONFIG } from '../../config';

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const ws = useRef<WebSocket | null>(null);
  const mounted = useRef(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (!mounted.current || !token) return;

      const socket = new WebSocket(`${CONFIG.WS_BASE_URL}?token=${encodeURIComponent(token)}`);
      ws.current = socket;

      socket.onopen = () => {
        if (ws.current !== socket) return;
        console.log('WebSocket Connected');
        setIsConnected(true);
      };

      socket.onmessage = (e) => {
        if (ws.current !== socket) return;
        try {
          const data = JSON.parse(e.data);
          setLastMessage(data);
        } catch {
          // Binary or non-json message
          setLastMessage(e.data);
        }
      };

      socket.onerror = () => {
        if (ws.current === socket) setIsConnected(false);
        // WebSocket is optional; HTTP-backed screens continue independently.
        console.warn('WebSocket connection failed; continuing with HTTP.');
        socket.close();
      };

      socket.onclose = () => {
        if (ws.current !== socket) return;
        ws.current = null;
        setIsConnected(false);
        if (mounted.current && !reconnectTimer.current) {
          reconnectTimer.current = setTimeout(() => {
            reconnectTimer.current = null;
            void connect();
          }, 3000);
        }
      };
    } catch {
      if (!mounted.current) return;
      setIsConnected(false);
      console.warn('WebSocket unavailable; continuing with HTTP.');
      if (mounted.current && !reconnectTimer.current) {
        reconnectTimer.current = setTimeout(() => {
          reconnectTimer.current = null;
          void connect();
        }, 3000);
      }
    }
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
    mounted.current = true;
    void connect();
    return () => {
      mounted.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
      const socket = ws.current;
      ws.current = null;
      socket?.close();
    };
  }, [connect]);

  return { isConnected, lastMessage, sendMessage };
};
