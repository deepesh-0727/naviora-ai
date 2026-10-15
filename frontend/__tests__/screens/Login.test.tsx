import React from 'react';
import { act, fireEvent, render } from '@testing-library/react-native';
import LoginScreen from '../../src/patient/screens/Login';

const mockLoginWithCredentials = jest.fn();
jest.mock('../../src/context/AuthContext', () => ({ useAuth: () => ({ loginWithCredentials: mockLoginWithCredentials }) }));
jest.mock('../../src/context/ThemeContext', () => ({ useTheme: () => ({ colors: { gradients: { primary: ['#000', '#111'] }, error: '#f00' } }) }));
jest.mock('expo-linear-gradient', () => ({ LinearGradient: require('react-native').View }));
jest.mock('expo-status-bar', () => ({ StatusBar: () => null }));
jest.mock('react-native-reanimated', () => {
  const React = require('react');
  const { View } = require('react-native');
  const animation = { delay: () => animation, duration: () => animation };
  return { __esModule: true, default: { View }, FadeInDown: animation, FadeInUp: animation };
});
jest.mock('../../src/components/common/AtomicComponents', () => {
  const React = require('react');
  const { Text, TextInput, View, Pressable } = require('react-native');
  return {
    NavioraText: ({ children }: any) => <Text>{children}</Text>,
    GlassCard: ({ children }: any) => <View>{children}</View>,
    StatusBadge: ({ text }: any) => <Text>{text}</Text>,
    FloatingLabelInput: ({ label, value, onChangeText, ...props }: any) => <TextInput accessibilityLabel={label} value={value} onChangeText={onChangeText} {...props} />,
    GradientButton: ({ title, onPress }: any) => <Pressable accessibilityRole="button" onPress={onPress}><Text>{title}</Text></Pressable>,
  };
});

describe('LoginScreen', () => {
  beforeEach(() => jest.clearAllMocks());

  it('validates required credentials before calling login', () => {
    const screen = render(<LoginScreen navigation={{ navigate: jest.fn() }} route={{ params: { zone: 'patient' }}} />);
    fireEvent.press(screen.getByText('Sign In'));
    expect(screen.getByText('Enter your email address or phone number.')).toBeTruthy();
    expect(mockLoginWithCredentials).not.toHaveBeenCalled();
  });

  it('submits normalized credentials for the selected staff zone', async () => {
    mockLoginWithCredentials.mockResolvedValue({ success: true });
    const screen = render(<LoginScreen navigation={{ navigate: jest.fn() }} route={{ params: { zone: 'staff' }}} />);
    fireEvent.changeText(screen.getByLabelText('Staff email or phone number'), ' staff@example.com ');
    fireEvent.changeText(screen.getByLabelText('Password'), 'secret');
    await act(async () => fireEvent.press(screen.getByText('Sign In')));
    expect(mockLoginWithCredentials).toHaveBeenCalledWith('staff@example.com', 'secret', 'staff');
  });
});
