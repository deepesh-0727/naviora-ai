import React from 'react';
import { createDrawerNavigator, DrawerContentScrollView, DrawerItem, DrawerItemList, type DrawerContentComponentProps } from '@react-navigation/drawer';
import { Ionicons } from '@expo/vector-icons';
import { RoleGuard } from '../../shared/guards/RoleGuard';
import { useAuth } from '../../context/AuthContext';
import { useRole } from '../../shared/contexts/RoleContext';
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
import { colors } from '../../shared/theme/colors';

const Drawer = createDrawerNavigator();

function AdminDrawerContent(props: DrawerContentComponentProps) {
  const { signOut } = useAuth();
  const { logout } = useRole();

  const handleLogout = async () => {
    await Promise.allSettled([signOut(), logout()]);
  };

  return <DrawerContentScrollView {...props}>
    <DrawerItemList {...props} />
    <DrawerItem
      label="Logout"
      onPress={() => void handleLogout()}
      icon={({ color, size }) => <Ionicons name="log-out-outline" color={color} size={size} />}
      labelStyle={{ color: colors.danger, fontWeight: '600' }}
    />
  </DrawerContentScrollView>;
}

function AdminDrawer() {
  return <Drawer.Navigator screenOptions={{
    headerTitleAlign: 'center',
    headerStyle: { backgroundColor: colors.white },
    headerTintColor: colors.primary,
    headerTitleStyle: { color: colors.text, fontWeight: '700' },
    drawerStyle: { backgroundColor: colors.background },
    drawerActiveTintColor: colors.primary,
    drawerActiveBackgroundColor: colors.primaryLight,
    drawerInactiveTintColor: colors.textMuted,
    sceneContainerStyle: { backgroundColor: colors.background },
  }} drawerContent={(props) => <AdminDrawerContent {...props} />}>
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
