import { act, renderHook, waitFor } from '@testing-library/react-native';
import { api } from '../../src/shared/services/api';
import { websocketClient } from '../../src/shared/services/websocket';
import { useEmergency } from '../../src/patient/hooks/useEmergency';

jest.mock('../../src/shared/services/api', () => ({
  api: { patient: { triggerEmergency: jest.fn(), cancelEmergency: jest.fn() } },
}));

jest.mock('../../src/shared/services/websocket', () => ({
  websocketClient: { connect: jest.fn(), subscribe: jest.fn(() => jest.fn()) },
}));

const patientApi = api.patient as jest.Mocked<typeof api.patient>;

describe('useEmergency', () => {
  beforeEach(() => jest.clearAllMocks());

  it('triggers an emergency with location and condition, then cancels the returned case', async () => {
    const activeCase = { id: 12, status: 'active', location: 'Ward 3' };
    patientApi.triggerEmergency.mockResolvedValue({ data: activeCase } as any);
    patientApi.cancelEmergency.mockResolvedValue({ data: { ...activeCase, status: 'cancelled' } } as any);
    const { result } = renderHook(() => useEmergency());
    await waitFor(() => expect(websocketClient.connect).toHaveBeenCalled());

    await act(async () => {
      await result.current.trigger({ lat: 12.97, lng: 77.59 }, 'breathing difficulty', 'patient-2');
    });

    expect(result.current.status).toBe('active');
    expect(result.current.emergencyCase).toEqual(activeCase);
    expect(patientApi.triggerEmergency).toHaveBeenCalledWith({
      location: { lat: 12.97, lng: 77.59 },
      condition: 'breathing difficulty',
      patient_id: 'patient-2',
    });

    await act(async () => result.current.cancel());
    expect(patientApi.cancelEmergency).toHaveBeenCalledWith(12);
    expect(result.current.status).toBe('cancelled');
  });
});
