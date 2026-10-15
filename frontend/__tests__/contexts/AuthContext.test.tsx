import React from 'react';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import { Text, Pressable } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { AuthProvider, useAuth } from '../../src/context/AuthContext';
import { apiService } from '../../src/services/api';

jest.mock('../../src/services/api', () => ({ apiService: { postForm: jest.fn(), get: jest.fn() } }));
jest.mock('@react-native-async-storage/async-storage', () => require('@react-native-async-storage/async-storage/jest/async-storage-mock'));

function Probe() {
  const auth = useAuth();
  return <>
    <Text testID="loading">{String(auth.isLoading)}</Text>
    <Text testID="role">{auth.user?.role || 'none'}</Text>
    <Pressable testID="login" onPress={() => void auth.loginWithCredentials(' patient@example.com ', 'secret')} />
    <Pressable testID="staff-login" onPress={() => void auth.loginWithCredentials('staff@example.com', 'secret', 'staff')} />
    <Pressable testID="logout" onPress={() => void auth.signOut()} />
  </>;
}

describe('AuthProvider', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await AsyncStorage.clear();
  });

  it('restores a stored user and clears auth storage on logout', async () => {
    await AsyncStorage.setItem('auth_user', JSON.stringify({ id: 'p1', name: 'Pat', email: 'p@test', role: 'patient' }));
    const screen = render(<AuthProvider><Probe /></AuthProvider>);
    await waitFor(() => expect(screen.getByTestId('role').props.children).toBe('patient'));
    await act(async () => fireEvent.press(screen.getByTestId('logout')));
    expect(screen.getByTestId('role').props.children).toBe('none');
    expect(await AsyncStorage.getItem('auth_user')).toBeNull();
    expect(await AsyncStorage.getItem('access_token')).toBeNull();
  }, 15000);

  it('stores tokens for a valid patient login and rejects a role from the wrong zone', async () => {
    (apiService.postForm as jest.Mock)
      .mockResolvedValue({ data: { access_token: 'access-1', refresh_token: 'refresh-1' } });
    (apiService.get as jest.Mock).mockResolvedValue({ data: { id: 1, full_name: 'Patient', role: 'patient' } });
    const screen = render(<AuthProvider><Probe /></AuthProvider>);
    await waitFor(() => expect(screen.getByTestId('loading').props.children).toBe('false'));
    await act(async () => fireEvent.press(screen.getByTestId('login')));
    expect(await AsyncStorage.getItem('access_token')).toBe('access-1');
    expect(await AsyncStorage.getItem('refresh_token')).toBe('refresh-1');
    expect(JSON.parse((await AsyncStorage.getItem('auth_user'))!).role).toBe('patient');

    (apiService.get as jest.Mock).mockResolvedValue({ data: { id: 2, full_name: 'Patient', role: 'patient' } });
    await act(async () => fireEvent.press(screen.getByTestId('staff-login')));
    expect(await AsyncStorage.getItem('access_token')).toBeNull();
  });
});
