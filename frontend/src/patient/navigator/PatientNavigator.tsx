import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';

import DashboardScreen from '../../screens/Dashboard';
import AppointmentScreen from '../../screens/Appointment';
import VoiceAssistantScreen from '../../screens/VoiceAssistant';
import NotificationsScreen from '../../screens/Notifications';
import ProfileScreen from '../../screens/Profile';
import NavigationScreen from '../../screens/Navigation';
import EmergencyScreen from '../../screens/Emergency';
import SettingsScreen from '../../screens/Settings';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

function PatientTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="Home" component={DashboardScreen} />
      <Tab.Screen name="Appointments" component={AppointmentScreen} />
      <Tab.Screen name="Voice" component={VoiceAssistantScreen} />
      <Tab.Screen name="Notifications" component={NotificationsScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

export default function PatientNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="PatientTabs" component={PatientTabs} />
      <Stack.Screen name="Navigation" component={NavigationScreen} />
      <Stack.Screen name="Emergency" component={EmergencyScreen} />
      <Stack.Screen name="Settings" component={SettingsScreen} />
    </Stack.Navigator>
  );
}
