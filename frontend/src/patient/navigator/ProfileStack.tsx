/**
 * ProfileStack — wraps Profile and Settings screens.
 */
import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import ProfileScreen from '../../screens/Profile';
import SettingsScreen from '../../screens/Settings';

export type ProfileStackParamList = {
  ProfileMain: undefined;
  Settings: undefined;
};

const Stack = createStackNavigator<ProfileStackParamList>();

export default function ProfileStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="ProfileMain" component={ProfileScreen} />
      <Stack.Screen name="Settings" component={SettingsScreen} />
    </Stack.Navigator>
  );
}
