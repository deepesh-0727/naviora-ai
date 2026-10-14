import { CONFIG } from '../../../config';
import { getAccessToken } from './secure_store';

type Listener = (payload: unknown) => void;
export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';
type StateListener = (state: ConnectionState) => void;

const MAX_OFFLINE_MESSAGES = 100;
const HEARTBEAT_INTERVAL_MS = 30000;
const HEARTBEAT_TIMEOUT_MS = 10000;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private listeners = new Map<string, Set<Listener>>();
  private stateListeners = new Set<StateListener>();
  private reconnectDelayMs = 1000;
  private readonly maxReconnectDelayMs = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
  private connected = false;
  private explicitlyDisconnected = false;
  private everConnected = false;
  private state: ConnectionState = 'disconnected';
  private rooms = new Set<string>();
  private outgoingQueue: string[] = [];
  private heartbeatSequence = 0;
  private pendingHeartbeat: string | null = null;
  private connectionAttempt = 0;

  async connect(room?: string): Promise<void> {
    const attempt = ++this.connectionAttempt;
    this.explicitlyDisconnected = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    if (room) this.rooms.add(room);
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)
    ) {
      if (this.connected) this.resubscribeRooms();
      return;
    }

    this.setState(this.everConnected ? 'reconnecting' : 'connecting');
    const token = await getAccessToken();
    if (attempt !== this.connectionAttempt || this.explicitlyDisconnected) return;
    if (!token) {
      this.setState('disconnected');
      this.emit('connection_error', new Error('WebSocket connection requires an authenticated session.'));
      return;
    }

    this.addClaimRooms(token);
    const socket = new WebSocket(`${CONFIG.WS_BASE_URL}?token=${encodeURIComponent(token)}`);
    this.socket = socket;
    socket.onopen = () => {
      if (this.socket !== socket) return;
      this.connected = true;
      this.everConnected = true;
      this.reconnectDelayMs = 1000;
      this.setState('connected');
      this.resubscribeRooms();
      this.flushOutgoingQueue();
      this.heartbeatTimer = setInterval(() => this.sendHeartbeat(), HEARTBEAT_INTERVAL_MS);
    };
    socket.onmessage = (event) => this.handleMessage(socket, event.data);
    socket.onerror = () => this.emit('connection_error', new Error('WebSocket connection failed.'));
    socket.onclose = () => {
      if (this.socket !== socket) return;
      this.connected = false;
      this.socket = null;
      this.clearHeartbeat();
      this.setState('disconnected');
      if (!this.explicitlyDisconnected) this.scheduleReconnect();
    };
  }

  disconnect(): void {
    this.connectionAttempt += 1;
    this.explicitlyDisconnected = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.clearHeartbeat();
    const socket = this.socket;
    this.socket = null;
    this.connected = false;
    this.setState('disconnected');
    if (socket) socket.close();
  }

  send(message: unknown): void {
    const serialized = typeof message === 'string' ? message : JSON.stringify(message);
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(serialized);
      return;
    }
    if (this.outgoingQueue.length === MAX_OFFLINE_MESSAGES) this.outgoingQueue.shift();
    this.outgoingQueue.push(serialized);
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

  onStateChange(callback: StateListener): () => void {
    this.stateListeners.add(callback);
    callback(this.state);
    return () => this.stateListeners.delete(callback);
  }

  isConnected(): boolean {
    return this.connected;
  }

  private handleMessage(socket: WebSocket, rawData: unknown): void {
    let payload: unknown;
    try {
      payload = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
    } catch {
      this.emit('message', rawData);
      return;
    }

    if (typeof payload === 'object' && payload !== null) {
      const record = payload as Record<string, unknown>;
      if (record.action === 'ping') {
        if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ action: 'pong' }));
        return;
      }
      if (record.action === 'pong') {
        this.clearHeartbeatTimeout();
        this.pendingHeartbeat = null;
      }
      const eventName = typeof record.event === 'string'
        ? record.event
        : typeof record.action === 'string'
          ? record.action
          : typeof record.type === 'string'
            ? record.type
            : 'message';
      this.emit(eventName, payload);
      this.emit('message', payload);
      return;
    }
    this.emit('message', payload);
  }

  private addClaimRooms(token: string): void {
    try {
      const encoded = token.split('.')[1];
      if (!encoded) return;
      const normalized = encoded.replace(/-/g, '+').replace(/_/g, '/');
      const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');
      const claims = JSON.parse(atob(padded)) as Record<string, unknown>;
      const role = claims.role;
      const staffId = claims.staff_id ?? claims.sub;
      if (role === 'patient') this.rooms.add(`patient:${claims.patient_id ?? claims.sub}`);
      if (role === 'doctor') this.rooms.add(`doctor:${staffId}`);
      if (role === 'nurse') this.rooms.add(`nurse:${staffId}`);
      if (typeof claims.ward_id === 'string' || typeof claims.ward_id === 'number') {
        this.rooms.add(`ward:${claims.ward_id}`);
      }
      if (role === 'doctor' || role === 'nurse' || role === 'front_desk' || role === 'pharmacy' || role === 'facilities' || role === 'emergency' || role === 'staff' || role === 'admin' || role === 'super_admin') {
        this.rooms.add(`staff:${claims.sub}`);
      }
      if (role === 'doctor' || role === 'nurse' || role === 'front_desk' || role === 'staff' || role === 'admin' || role === 'super_admin') {
        this.rooms.add('queue:all');
      }
      if (role === 'doctor' || role === 'nurse' || role === 'emergency' || role === 'staff' || role === 'admin' || role === 'super_admin') this.rooms.add('emergency');
      if (role === 'pharmacy' || role === 'staff' || role === 'admin' || role === 'super_admin') this.rooms.add('pharmacy');
      if (role === 'facilities' || role === 'staff' || role === 'admin' || role === 'super_admin') this.rooms.add('facilities');
      if (role === 'admin' || role === 'super_admin') this.rooms.add('admin');
    } catch {
      this.emit('connection_error', new Error('Unable to restore WebSocket room subscriptions.'));
    }
  }

  private resubscribeRooms(): void {
    for (const room of this.rooms) this.sendDirect({ action: 'join_room', room });
  }

  private sendDirect(message: unknown): void {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify(message));
  }

  private flushOutgoingQueue(): void {
    while (this.outgoingQueue.length > 0 && this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(this.outgoingQueue.shift() as string);
    }
  }

  private sendHeartbeat(): void {
    if (this.socket?.readyState !== WebSocket.OPEN || this.pendingHeartbeat) return;
    const heartbeatId = String(++this.heartbeatSequence);
    this.pendingHeartbeat = heartbeatId;
    this.socket.send(JSON.stringify({ action: 'ping', heartbeat_id: heartbeatId }));
    this.heartbeatTimeout = setTimeout(() => {
      if (this.pendingHeartbeat !== heartbeatId) return;
      this.pendingHeartbeat = null;
      this.socket?.close();
    }, HEARTBEAT_TIMEOUT_MS);
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    const delay = Math.min(this.reconnectDelayMs, this.maxReconnectDelayMs);
    this.reconnectDelayMs = Math.min(this.reconnectDelayMs * 2, this.maxReconnectDelayMs);
    this.setState('reconnecting');
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      void this.connect();
    }, delay);
  }

  private clearHeartbeat(): void {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = null;
    this.clearHeartbeatTimeout();
    this.pendingHeartbeat = null;
  }

  private clearHeartbeatTimeout(): void {
    if (this.heartbeatTimeout) clearTimeout(this.heartbeatTimeout);
    this.heartbeatTimeout = null;
  }

  private setState(state: ConnectionState): void {
    if (this.state === state) return;
    this.state = state;
    this.stateListeners.forEach((callback) => callback(state));
    this.emit('connection_status', { state, connected: state === 'connected' });
  }

  private emit(event: string, payload: unknown): void {
    this.listeners.get(event)?.forEach((callback) => callback(payload));
  }
}

export const websocketClient = new WebSocketClient();
