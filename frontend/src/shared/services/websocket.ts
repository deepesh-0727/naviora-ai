import { CONFIG } from '../../../config';
import { getAccessToken } from './secure_store';

type Listener = (payload: unknown) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private listeners = new Map<string, Set<Listener>>();
  private reconnectDelayMs = 1000;
  private readonly maxReconnectDelayMs = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private connected = false;
  private explicitlyDisconnected = false;
  private room: string | null = null;

  async connect(room?: string): Promise<void> {
    this.explicitlyDisconnected = false;
    this.room = room ?? this.room;
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)
    ) {
      if (this.connected && this.room) this.joinRoom(this.room);
      return;
    }

    const token = await getAccessToken();
    if (!token) {
      this.emit('connection_error', new Error('WebSocket connection requires an authenticated session.'));
      return;
    }

    const socket = new WebSocket(`${CONFIG.WS_BASE_URL}?token=${encodeURIComponent(token)}`);
    this.socket = socket;
    socket.onopen = () => {
      if (this.socket !== socket) return;
      this.connected = true;
      this.reconnectDelayMs = 1000;
      this.emit('connection_status', { connected: true });
      if (this.room) this.joinRoom(this.room);
      this.heartbeatTimer = setInterval(() => this.send({ action: 'ping' }), 30000);
    };
    socket.onmessage = (event) => {
      try {
        const payload: unknown = JSON.parse(event.data);
        if (typeof payload === 'object' && payload !== null) {
          const record = payload as Record<string, unknown>;
          const eventName = typeof record.action === 'string'
            ? record.action
            : typeof record.type === 'string'
              ? record.type
              : 'message';
          this.emit(eventName, payload);
          this.emit('message', payload);
        } else {
          this.emit('message', payload);
        }
      } catch {
        this.emit('message', event.data);
      }
    };
    socket.onerror = () => this.emit('connection_error', new Error('WebSocket connection failed.'));
    socket.onclose = () => {
      if (this.socket !== socket) return;
      this.connected = false;
      this.socket = null;
      this.clearHeartbeat();
      this.emit('connection_status', { connected: false });
      if (!this.explicitlyDisconnected) this.scheduleReconnect();
    };
  }

  disconnect(): void {
    this.explicitlyDisconnected = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.clearHeartbeat();
    const socket = this.socket;
    this.socket = null;
    this.connected = false;
    if (socket) socket.close();
  }

  send(message: unknown): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }

  subscribe(event: string, callback: Listener): () => void {
    let callbacks = this.listeners.get(event);
    if (!callbacks) {
      callbacks = new Set<Listener>();
      this.listeners.set(event, callbacks);
    }
    callbacks.add(callback);
    return () => this.unsubscribe(event, callback);
  }

  unsubscribe(event: string, callback: Listener): void {
    const callbacks = this.listeners.get(event);
    if (!callbacks) return;
    callbacks.delete(callback);
    if (callbacks.size === 0) this.listeners.delete(event);
  }

  isConnected(): boolean {
    return this.connected;
  }

  private joinRoom(room: string): void {
    this.send({ action: 'join_room', room });
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    const delay = Math.min(this.reconnectDelayMs, this.maxReconnectDelayMs);
    this.reconnectDelayMs = Math.min(this.reconnectDelayMs * 2, this.maxReconnectDelayMs);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      void this.connect();
    }, delay);
  }

  private clearHeartbeat(): void {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = null;
  }

  private emit(event: string, payload: unknown): void {
    this.listeners.get(event)?.forEach((callback) => callback(payload));
  }
}

export const websocketClient = new WebSocketClient();
