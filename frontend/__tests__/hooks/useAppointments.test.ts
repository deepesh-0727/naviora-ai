import { act, renderHook, waitFor } from '@testing-library/react-native';
import { api } from '../../src/shared/services/api';
import { useAppointments } from '../../src/patient/hooks/useAppointments';

jest.mock('../../src/shared/services/api', () => ({
  api: {
    patient: {
      getAppointments: jest.fn(),
      getDepartments: jest.fn(),
      getDoctors: jest.fn(),
      getAppointmentAvailability: jest.fn(),
      createAppointment: jest.fn(),
      cancelAppointment: jest.fn(),
      rescheduleAppointment: jest.fn(),
    },
  },
}));

const patientApi = api.patient as jest.Mocked<typeof api.patient>;

describe('useAppointments', () => {
  beforeEach(() => {
    jest.useFakeTimers().setSystemTime(new Date('2026-01-10T00:00:00.000Z'));
    jest.clearAllMocks();
    patientApi.getAppointments.mockResolvedValue({ data: [
      { id: 2, scheduled_time: '2026-01-11T10:00:00.000Z' },
      { id: 1, scheduled_time: '2026-01-09T10:00:00.000Z' },
    ] } as any);
    patientApi.getDepartments.mockResolvedValue({ data: [{ id: 4, name: 'Cardiology' }] } as any);
  });

  afterEach(() => jest.useRealTimers());

  it('loads and separates upcoming and past appointments', async () => {
    const { result } = renderHook(() => useAppointments());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.upcoming.map(item => item.id)).toEqual([2]);
    expect(result.current.past.map(item => item.id)).toEqual([1]);
    expect(result.current.departments).toEqual([{ id: 4, name: 'Cardiology' }]);
  });

  it('books and cancels an appointment, refreshing the real API state', async () => {
    patientApi.createAppointment.mockResolvedValue({ data: { id: 3 } } as any);
    patientApi.cancelAppointment.mockResolvedValue({ data: { status: 'cancelled' } } as any);
    const { result } = renderHook(() => useAppointments());
    await waitFor(() => expect(result.current.loading).toBe(false));
    const appointment = {
      doctor_id: 8,
      department_id: 4,
      scheduled_time: '2026-01-11T10:00:00.000Z',
      symptoms: 'persistent cough',
    };

    await act(async () => {
      await expect(result.current.book(appointment)).resolves.toEqual({ id: 3 });
    });
    await act(async () => {
      await expect(result.current.cancel(3)).resolves.toBe(true);
    });

    expect(patientApi.createAppointment).toHaveBeenCalledWith(appointment);
    expect(patientApi.cancelAppointment).toHaveBeenCalledWith(3);
    expect(patientApi.getAppointments).toHaveBeenCalledTimes(3);
  });
});
