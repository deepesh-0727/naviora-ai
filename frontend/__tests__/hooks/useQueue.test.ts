import { act, renderHook, waitFor } from '@testing-library/react-native';
import { api } from '../../src/shared/services/api';
import { websocketClient } from '../../src/shared/services/websocket';
import { useQueue } from '../../src/patient/hooks/useQueue';

jest.mock('../../src/shared/services/api', () => ({
  api: { patient: { getAppointments: jest.fn() } },
}));
jest.mock('../../src/shared/services/websocket', () => ({
  websocketClient: { connect: jest.fn(), subscribe: jest.fn() },
}));

const getAppointments = api.patient.getAppointments as jest.Mock;
const listeners: Record<string, () => void> = {};

describe('useQueue', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (websocketClient.subscribe as jest.Mock).mockImplementation((event: string, cb: () => void) => {
      listeners[event] = cb;
      return jest.fn();
    });
    getAppointments.mockResolvedValue({ data: [{ id: 7, status: 'waiting' }] });
  });

  it('fetches upcoming appointments and refreshes on websocket queue updates', async () => {
    const { result } = renderHook(() => useQueue());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(getAppointments).toHaveBeenCalledWith({ upcoming: true });
    expect(result.current.appointments).toEqual([{ id: 7, status: 'waiting' }]);

    await act(async () => listeners.queue_update());
    await waitFor(() => expect(getAppointments).toHaveBeenCalledTimes(2));
  });

  it('reports retryable errors and unsubscribes listeners on unmount', async () => {
    const unsubscribeQueue = jest.fn();
    const unsubscribeAppointment = jest.fn();
    (websocketClient.subscribe as jest.Mock)
      .mockReturnValueOnce(unsubscribeQueue)
      .mockReturnValueOnce(unsubscribeAppointment);
    getAppointments.mockRejectedValue(new Error('offline'));
    const { result, unmount } = renderHook(() => useQueue());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe('Failed to load queue. Please retry.');
    unmount();
    expect(unsubscribeQueue).toHaveBeenCalledTimes(1);
    expect(unsubscribeAppointment).toHaveBeenCalledTimes(1);
  });
});
