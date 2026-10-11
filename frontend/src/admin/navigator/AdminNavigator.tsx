import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import AdminDashboardScreen from '../../screens/admin/Dashboard';
import StaffManagementScreen from '../../screens/admin/StaffManagement';
import DepartmentsScreen from '../../screens/admin/Departments';
import AdminAnalyticsScreen from '../../screens/admin/Analytics';
import AuditLogsScreen from '../../screens/admin/AuditLogs';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

function AdminTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="Dashboard" component={AdminDashboardScreen} />
      <Tab.Screen name="Users" component={StaffManagementScreen} />
      <Tab.Screen name="Departments" component={DepartmentsScreen} />
      <Tab.Screen name="Analytics" component={AdminAnalyticsScreen} />
    </Tab.Navigator>
  );
}

export default function AdminNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="AdminTabs" component={AdminTabs} />
      <Stack.Screen name="AuditLogs" component={AuditLogsScreen} />
    </Stack.Navigator>
  );
}
