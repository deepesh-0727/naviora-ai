import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import { Text, View } from 'react-native';
import DashboardScreen from '../../src/screens/Dashboard';
import { apiService } from '../../src/services/api';

const mockSetQueueData = jest.fn();
jest.mock('../../src/services/api', () => ({ apiService: { get: jest.fn() } }));
jest.mock('../../src/context/ThemeContext', () => ({ useTheme: () => ({ colors: { background: '#fff', gradients: { primary: ['#000', '#111'], accent: ['#222', '#333'] }, primary: '#00f', accent: '#0f0', purple: '#f0f', error: '#f00', warning: '#fa0', status: { live: '#0f0' }, glass: { border: '#ddd' }, text: { low: '#555' } } }) }));
jest.mock('../../src/context/QueueContext', () => ({ useQueue: () => ({ queueData: null, setQueueData: mockSetQueueData }) }));
jest.mock('../../src/context/ProfileContext', () => ({ useProfile: () => ({ profile: { id: 'p1', name: 'Patient' } }) }));
jest.mock('expo-linear-gradient', () => ({ LinearGradient: require('react-native').View }));
jest.mock('expo-status-bar', () => ({ StatusBar: () => null }));
jest.mock('react-native-reanimated', () => {
  const { View } = require('react-native');
  const animation = { delay: () => animation, duration: () => animation };
  return { __esModule: true, default: { View }, FadeInDown: animation, FadeInRight: animation };
});
jest.mock('../../src/components/common/AtomicComponents', () => {
  const { Text, View } = require('react-native');
  return { NavioraText: ({ children }: any) => <Text>{children}</Text>, GlassCard: ({ children }: any) => <View>{children}</View>, StatusBadge: ({ text }: any) => <Text>{text}</Text> };
});

describe('DashboardScreen', () => {
  beforeEach(() => { jest.clearAllMocks(); });

  it('loads queue and appointment data into dashboard state', async () => {
    (apiService.get as jest.Mock)
      .mockResolvedValueOnce({ data: { queue: [{ position: 3, status: 'waiting', doctor_name: 'Dr Lee' }], total_waiting: 5, average_wait_minutes: 20 } })
      .mockResolvedValueOnce({ data: [{ id: 1, doctor_name: 'Dr Lee', department_name: 'Cardiology', status: 'scheduled', scheduled_time: '2026-10-16T09:30:00Z' }] });
    const screen = render(<DashboardScreen navigation={{ navigate: jest.fn() }} />);
    await waitFor(() => expect(screen.getByText('Dr Lee')).toBeTruthy());
    expect(apiService.get).toHaveBeenNthCalledWith(1, '/appointments/queue');
    expect(apiService.get).toHaveBeenNthCalledWith(2, '/appointments');
    expect(mockSetQueueData).toHaveBeenCalledWith({ position: 3, estimatedWait: 20, status: 'waiting', doctorName: 'Dr Lee' });
    expect(screen.getByText('Cardiology')).toBeTruthy();
  });

  it('renders the empty appointments state', async () => {
    (apiService.get as jest.Mock).mockResolvedValueOnce({ data: { queue: [] } }).mockResolvedValueOnce({ data: [] });
    const screen = render(<DashboardScreen navigation={{ navigate: jest.fn() }} />);
    await waitFor(() => expect(screen.getByText('No active appointments scheduled for today.')).toBeTruthy());
  });
});
