import AsyncStorage from '@react-native-async-storage/async-storage';

// Replace with your local FastAPI server IP address when debugging on physical devices
const WS_URL = 'ws://localhost:8000/api/v1/stream';

type WebSocketMessage = {
  action: string;
  [key: string]: any;
};

type MessageCallback = (data: any) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private listeners: Map<string, Set<MessageCallback>> = new Map();
  private reconnectInterval = 3000;
  private maxReconnectAttempts = 5;
  private reconnectAttempts = 0;
  private isIntentionalDisconnect = false;

  public async connect(): Promise<void> {
    this.isIntentionalDisconnect = false;
    const token = await AsyncStorage.getItem('access_token');
    
    if (!token) {
      console.warn('WebSocket connection aborted: access token missing.');
      return;
    }

    const url = `${WS_URL}?token=${encodeURIComponent(token)}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log('WebSocket successfully connected.');
      this.reconnectAttempts = 0;
      this.emit('connection_status', { connected: true });
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const action = data.action || 'message';
        this.emit(action, data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket connection error:', error);
    };

    this.socket.onclose = () => {
      console.log('WebSocket closed.');
      this.emit('connection_status', { connected: false });
      
      if (!this.isIntentionalDisconnect) {
        this.attemptReconnect();
      }
    };
  }

  public disconnect(): void {
    this.isIntentionalDisconnect = true;
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  public send(action: string, payload: Record<string, any> = {}): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = { action, ...payload };
      this.socket.send(JSON.stringify(message));
    } else {
      console.warn('Cannot send message: WebSocket is not open.');
    }
  }

  public subscribe(event: string, callback: MessageCallback): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    // Return unsubscribe function
    return () => {
      const eventListeners = this.listeners.get(event);
      if (eventListeners) {
        eventListeners.delete(callback);
        if (eventListeners.size === 0) {
          this.listeners.delete(event);
        }
      }
    };
  }

  private emit(event: string, data: any): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach((callback) => callback(data));
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max WebSocket reconnection attempts reached.');
      return;
    }

    this.reconnectAttempts += 1;
    console.log(`Reconnecting WebSocket in ${this.reconnectInterval}ms (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    setTimeout(() => {
      this.connect();
    }, this.reconnectInterval);
  }
}

export const wsClient = new WebSocketClient();
