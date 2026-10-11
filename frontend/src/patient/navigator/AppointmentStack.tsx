/**
 * AppointmentStack — wraps Appointment list, detail, and booking sub-screens.
 */
import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import AppointmentScreen from '../screens/Appointment';

export type AppointmentStackParamList = {
  AppointmentList: undefined;
};

const Stack = createStackNavigator<AppointmentStackParamList>();

export default function AppointmentStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="AppointmentList" component={AppointmentScreen} />
    </Stack.Navigator>
  );
}
