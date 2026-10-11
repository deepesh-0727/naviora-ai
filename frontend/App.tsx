import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import 'react-native-gesture-handler';

import {
  useFonts,
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Inter_800ExtraBold,
} from '@expo-google-fonts/inter';

import { ThemeProvider } from './src/context/ThemeContext';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { ProfileProvider } from './src/context/ProfileContext';
import { QueueProvider } from './src/context/QueueContext';
import { AlertProvider } from './src/context/AlertContext';
import { LanguageProvider } from './src/context/LanguageContext';
import { RoleProvider } from './src/shared/contexts/RoleContext';
import { GlobalAlert } from './src/components/common/GlobalAlert';
import SplashScreen from './src/screens/Splash';
import RoleSelectScreen from './src/screens/RoleSelect';
import LoginScreen from './src/screens/Login';
import ForgotPasswordScreen from './src/screens/ForgotPassword';
import ResetPasswordScreen from './src/screens/ResetPassword';
import OTPScreen from './src/screens/OTP';
import RegistrationScreen from './src/screens/Registration';
import RoleBasedNavigator from './src/navigation/RoleBasedNavigator';

const Stack = createStackNavigator();

function RootNavigator() {
  const { user } = useAuth();
  const authenticated = user !== null;

  return (
    <NavigationContainer
      linking={{
        prefixes: ['com.naviora.ai://', 'exp+naviora-ai://'],
        config: { screens: { ResetPassword: 'reset-password' } },
      }}
    >
      <GlobalAlert />
      <Stack.Navigator
        key={authenticated ? `authenticated-${user.role}` : 'unauthenticated'}
        initialRouteName={authenticated ? 'Main' : 'Splash'}
        screenOptions={{
          headerStyle: {
            backgroundColor: '#F7F9F5',
            borderBottomWidth: 1,
            borderBottomColor: 'rgba(58, 90, 64, 0.12)',
          },
          headerTintColor: '#1A1A1A',
          headerTitleStyle: {
            fontWeight: 'bold',
            fontFamily: 'Inter_700Bold',
          },
          cardStyle: { backgroundColor: '#FAFAF7' },
          headerBackTitleVisible: false,
        }}
      >
        {authenticated ? (
          <>
            <Stack.Screen name="Main" component={RoleBasedNavigator} options={{ headerShown: false }} />
            <Stack.Screen name="ResetPassword" component={ResetPasswordScreen} options={{ headerShown: false }} />
          </>
        ) : (
          <>
            <Stack.Screen name="Splash" component={SplashScreen} options={{ headerShown: false }} />
            <Stack.Screen name="RoleSelect" component={RoleSelectScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
            <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} options={{ headerShown: false }} />
            <Stack.Screen name="ResetPassword" component={ResetPasswordScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Registration" component={RegistrationScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Register" component={RegistrationScreen} options={{ headerShown: false }} />
            <Stack.Screen name="OTP" component={OTPScreen} options={{ title: 'Verify OTP' }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    Inter_800ExtraBold,
  });

  if (!fontsLoaded) return null;

  return (
    <LanguageProvider>
      <ThemeProvider>
        <RoleProvider>
          <AuthProvider>
            <AlertProvider>
              <ProfileProvider>
                <QueueProvider>
                  <RootNavigator />
                </QueueProvider>
              </ProfileProvider>
            </AlertProvider>
          </AuthProvider>
        </RoleProvider>
      </ThemeProvider>
    </LanguageProvider>
  );
}
