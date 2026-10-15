import AsyncStorage from '@react-native-async-storage/async-storage';
import { wsClient } from '../../src/services/websocket';

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
}));

class FakeWebSocket {
  static OPEN = 1;
  static instances = 0;
  readyState = FakeWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((error: unknown) => void) | null = null;
  onclose: (() => void) | null = null;
  send = jest.fn();
  close = jest.fn();
  static lastUrl = '';

  constructor(url: string) {
    FakeWebSocket.instances += 1;
    FakeWebSocket.lastUrl = url;
  }
}

describe('WebSocket client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    FakeWebSocket.instances = 0;
    FakeWebSocket.lastUrl = '';
    (global as any).WebSocket = FakeWebSocket;
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue('token with spaces');
  });

  it('connects with an encoded token and delivers subscribed messages', async () => {
    const onMessage = jest.fn();
    const unsubscribe = wsClient.subscribe('queue_update', onMessage);

    await wsClient.connect();

    expect(FakeWebSocket.lastUrl).toContain('token=token%20with%20spaces');
    const socket = (wsClient as any).socket as FakeWebSocket;
    socket.onmessage?.({ data: JSON.stringify({ action: 'queue_update', position: 2 }) });
    expect(onMessage).toHaveBeenCalledWith({ action: 'queue_update', position: 2 });

    unsubscribe();
    socket.onmessage?.({ data: JSON.stringify({ action: 'queue_update', position: 1 }) });
    expect(onMessage).toHaveBeenCalledTimes(1);

    wsClient.disconnect();
    expect(socket.close).toHaveBeenCalledTimes(1);
  });

  it('does not connect when no access token is stored', async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => undefined);

    await wsClient.connect();

    expect(FakeWebSocket.instances).toBe(0);
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });
});
