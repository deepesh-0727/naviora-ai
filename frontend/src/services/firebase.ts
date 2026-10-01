import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiService } from './api';

export const registerPushToken = async (token: string, platform: string = 'android') => {
  try {
    await AsyncStorage.setItem('fcm_token', token);
    await apiService.post('/notifications/register-token', { token, platform });
    console.log('Push token registered successfully');
  } catch (error) {
    console.error('Failed to register push token', error);
  }
};

export const unregisterPushToken = async (token: string) => {
  try {
    await AsyncStorage.removeItem('fcm_token');
    await apiService.delete(`/notifications/unregister-token/${token}`);
    console.log('Push token unregistered successfully');
  } catch (error) {
    console.error('Failed to unregister push token', error);
  }
};
