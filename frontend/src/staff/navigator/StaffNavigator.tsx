import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';

import { useRole } from '../../shared/contexts/RoleContext';
import DoctorDashboardScreen from '../../screens/doctor/Dashboard';
import DoctorQueueScreen from '../../screens/doctor/Queue';
import PatientDetailsScreen from '../../screens/doctor/PatientDetails';
import NurseDashboardScreen from '../../screens/nurse/Dashboard';
import VitalsScreen from '../../screens/nurse/Vitals';
import AdminDashboardScreen from '../../screens/admin/Dashboard';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

function DoctorTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="DoctorHome" component={DoctorDashboardScreen} />
      <Tab.Screen name="DoctorQueue" component={DoctorQueueScreen} />
      <Tab.Screen name="PatientDetails" component={PatientDetailsScreen} />
    </Tab.Navigator>
  );
}

function NurseTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="NurseHome" component={NurseDashboardScreen} />
      <Tab.Screen name="Vitals" component={VitalsScreen} />
    </Tab.Navigator>
  );
}

function FrontDeskTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="Dashboard" component={AdminDashboardScreen} />
    </Tab.Navigator>
  );
}

export default function StaffNavigator() {
  const { role } = useRole();

  const roleTabs = role === 'doctor' ? <DoctorTabs /> : role === 'nurse' ? <NurseTabs /> : <FrontDeskTabs />;

  return <Stack.Navigator screenOptions={{ headerShown: false }}>{roleTabs && <Stack.Screen name="StaffTabs" component={() => roleTabs} />}</Stack.Navigator>;
}
