import React from 'react';
import { createDrawerNavigator } from '@react-navigation/drawer';
import { RoleGuard } from '../../shared/guards/RoleGuard';
import AdminDashboard from '../screens/AdminDashboard';
import PilotMetrics from '../screens/PilotMetrics';
import UserManagement from '../screens/UserManagement';
import AuditLog from '../screens/AuditLog';
import DepartmentManagement from '../screens/DepartmentManagement';
import ResourceManagement from '../screens/ResourceManagement';
import Analytics from '../screens/Analytics';
import Billing from '../screens/Billing';
import SystemHealth from '../screens/SystemHealth';
import Settings from '../screens/Settings';

const Drawer = createDrawerNavigator();

function AdminDrawer() {
  return <Drawer.Navigator screenOptions={{ headerTitleAlign: 'center' }}>
    <Drawer.Screen name="Dashboard" component={AdminDashboard} />
    <Drawer.Screen name="Pilot Metrics" component={PilotMetrics} />
    <Drawer.Screen name="Users" component={UserManagement} />
    <Drawer.Screen name="Audit Log" component={AuditLog} />
    <Drawer.Screen name="Departments" component={DepartmentManagement} />
    <Drawer.Screen name="Resources" component={ResourceManagement} />
    <Drawer.Screen name="Analytics" component={Analytics} />
    <Drawer.Screen name="Billing" component={Billing} />
    <Drawer.Screen name="System Health" component={SystemHealth} />
    <Drawer.Screen name="Settings" component={Settings} />
  </Drawer.Navigator>;
}

export default function AdminNavigator() {
  return <RoleGuard allow={['admin', 'super_admin']}><AdminDrawer /></RoleGuard>;
}
