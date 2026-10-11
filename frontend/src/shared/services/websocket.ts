type Listener = (payload: unknown) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private listeners = new Map<string, Set<Listener>>();
  private reconnectDelayMs = 1000;
  private maxReconnectDelayMs = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private connected = false;

  connect(url: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) return;

    this.socket = new WebSocket(url);
    this.socket.onopen = () => {
      this.connected = true;
      this.reconnectDelayMs = 1000;
      this.emit('connected', { connected: true });
    };
    this.socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const eventName = payload?.event ?? payload?.type ?? 'message';
        this.emit(eventName, payload);
      } catch {
        this.emit('message', event.data);
      }
    };
    this.socket.onerror = () => {
      this.emit('error', { connected: false });
    };
    this.socket.onclose = () => {
      this.connected = false;
      this.emit('closed', { connected: false });
      if (!this.reconnectTimer) {
        this.reconnectTimer = setTimeout(() => {
          this.reconnectTimer = null;
          if (this.socket) {
            this.socket.close();
          }
          if (url) {
            this.connect(url);
          }
        }, Math.min(this.reconnectDelayMs, this.maxReconnectDelayMs));
        this.reconnectDelayMs = Math.min(this.reconnectDelayMs * 2, this.maxReconnectDelayMs);
      }
    };
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.connected = false;
  }

  subscribe(event: string, callback: Listener) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)?.add(callback);

    return () => this.unsubscribe(event, callback);
  }

  unsubscribe(event: string, callback: Listener) {
    const handlers = this.listeners.get(event);
    if (!handlers) return;
    handlers.delete(callback);
    if (handlers.size === 0) {
      this.listeners.delete(event);
    }
  }

  send(message: unknown) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }

  isConnected() {
    return this.connected;
  }

  private emit(event: string, payload: unknown) {
    this.listeners.get(event)?.forEach((callback) => callback(payload));
  }
}

export const websocketClient = new WebSocketClient();

export const subscribeToRoleRoom = (
  role: string,
  roomId: string | null,
  callback: Listener
) => {
  const room = roomId ? `${role}:${roomId}` : role;
  return websocketClient.subscribe(room, callback);
};
