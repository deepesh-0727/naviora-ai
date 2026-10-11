/**
 * HomeStack — wraps Dashboard and any sub-routes under the Home tab.
 * Currently a single-screen stack; add sub-screens here as needed.
 */
import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import DashboardScreen from '../../screens/Dashboard';

export type HomeStackParamList = {
  Dashboard: undefined;
};

const Stack = createStackNavigator<HomeStackParamList>();

export default function HomeStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Dashboard" component={DashboardScreen} />
    </Stack.Navigator>
  );
}
