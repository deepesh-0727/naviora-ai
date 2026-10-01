import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Platform, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';

// Patient Screens
import DashboardScreen from '../screens/Dashboard';
import VoiceAssistantScreen from '../screens/VoiceAssistant';
import AppointmentScreen from '../screens/Appointment';
import NotificationsScreen from '../screens/Notifications';
import ProfileScreen from '../screens/Profile';
import NavigationScreen from '../screens/Navigation';
import EmergencyScreen from '../screens/Emergency';
import SettingsScreen from '../screens/Settings';
import TelehealthScreen from '../screens/Telehealth';
import PharmacyScreen from '../screens/Pharmacy';
import BillingScreen from '../screens/BillingScreen';

// Doctor Screens
import DoctorDashboardScreen from '../screens/doctor/Dashboard';
import DoctorQueueScreen from '../screens/doctor/Queue';
import PatientDetailsScreen from '../screens/doctor/PatientDetails';
import PrescriptionScreen from '../screens/doctor/Prescription';
import DoctorScheduleScreen from '../screens/doctor/Schedule';
import DoctorEmergencyScreen from '../screens/doctor/EmergencyResponse';
import DoctorAnalyticsScreen from '../screens/doctor/Analytics';
import DoctorProfileScreen from '../screens/doctor/Profile';

// Nurse Screens
import NurseDashboardScreen from '../screens/nurse/Dashboard';
import NurseCheckInScreen from '../screens/nurse/CheckIn';
import VitalsScreen from '../screens/nurse/Vitals';
import NurseQueueScreen from '../screens/nurse/Queue';
import NurseEmergencyScreen from '../screens/nurse/Emergency';
import NurseProfileScreen from '../screens/nurse/Profile';

// Admin Screens
import AdminDashboardScreen from '../screens/admin/Dashboard';
import StaffManagementScreen from '../screens/admin/StaffManagement';
import DepartmentsScreen from '../screens/admin/Departments';
import InventoryScreen from '../screens/admin/Inventory';
import AdminAnalyticsScreen from '../screens/admin/Analytics';
import AuditLogsScreen from '../screens/admin/AuditLogs';
import AdminProfileScreen from '../screens/admin/Profile';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

const tabOpts = {
  headerShown: false,
  tabBarShowLabel: false,
};

// ─── Patient Tab Navigator ────────────────────────────────────────────────────
function PatientTabs() {
  const theme = useTheme();
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        ...tabOpts,
        tabBarIcon: ({ focused, color, size }) => {
          const icons: Record<string, [string, string]> = {
            Home: ['home', 'home-outline'],
            Voice: ['mic', 'mic-outline'],
            Calendar: ['calendar', 'calendar-outline'],
            Alerts: ['notifications', 'notifications-outline'],
            Account: ['person', 'person-outline'],
          };
          const [active, inactive] = icons[route.name] || ['ellipse', 'ellipse-outline'];
          return (
            <View style={focused ? styles.activeTab : null}>
              <Ionicons name={(focused ? active : inactive) as any} size={size} color={color} />
            </View>
          );
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.text.low,
        tabBarStyle: styles.tabBar,
        tabBarBackground: () => (
          <BlurView
            intensity={26}
            tint="light"
            style={[StyleSheet.absoluteFill, { borderRadius: 35, overflow: 'hidden', borderWidth: 1, borderColor: theme.colors.border }]}
          />
        ),
      })}
    >
      <Tab.Screen name="Home" component={DashboardScreen} />
      <Tab.Screen name="Voice" component={VoiceAssistantScreen} />
      <Tab.Screen name="Calendar" component={AppointmentScreen} />
      <Tab.Screen name="Alerts" component={NotificationsScreen} />
      <Tab.Screen name="Account" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

// ─── Doctor Tab Navigator ─────────────────────────────────────────────────────
function DoctorTabs() {
  const theme = useTheme();
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        ...tabOpts,
        tabBarIcon: ({ focused, color, size }) => {
          const icons: Record<string, [string, string]> = {
            DocHome: ['grid', 'grid-outline'],
            DocQueue: ['list', 'list-outline'],
            DocSchedule: ['calendar', 'calendar-outline'],
            DocAnalytics: ['bar-chart', 'bar-chart-outline'],
            DocAccount: ['person', 'person-outline'],
          };
          const [active, inactive] = icons[route.name] || ['ellipse', 'ellipse-outline'];
          return (
            <View style={focused ? styles.activeTab : null}>
              <Ionicons name={(focused ? active : inactive) as any} size={size} color={color} />
            </View>
          );
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.text.low,
        tabBarStyle: styles.tabBar,
        tabBarBackground: () => (
          <BlurView
            intensity={26}
            tint="light"
            style={[StyleSheet.absoluteFill, { borderRadius: 35, overflow: 'hidden', borderWidth: 1, borderColor: theme.colors.border }]}
          />
        ),
      })}
    >
      <Tab.Screen name="DocHome" component={DoctorDashboardScreen} />
      <Tab.Screen name="DocQueue" component={DoctorQueueScreen} />
      <Tab.Screen name="DocSchedule" component={DoctorScheduleScreen} />
      <Tab.Screen name="DocAnalytics" component={DoctorAnalyticsScreen} />
      <Tab.Screen name="DocAccount" component={DoctorProfileScreen} />
    </Tab.Navigator>
  );
}

// ─── Nurse Tab Navigator ──────────────────────────────────────────────────────
function NurseTabs() {
  const theme = useTheme();
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        ...tabOpts,
        tabBarIcon: ({ focused, color, size }) => {
          const icons: Record<string, [string, string]> = {
            NurseHome: ['grid', 'grid-outline'],
            NurseQueue: ['list', 'list-outline'],
            NurseCheckIn: ['qr-code', 'qr-code-outline'],
            NurseVitals: ['pulse', 'pulse-outline'],
            NurseAccount: ['person', 'person-outline'],
          };
          const [active, inactive] = icons[route.name] || ['ellipse', 'ellipse-outline'];
          return (
            <View style={focused ? styles.activeTab : null}>
              <Ionicons name={(focused ? active : inactive) as any} size={size} color={color} />
            </View>
          );
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.text.low,
        tabBarStyle: styles.tabBar,
        tabBarBackground: () => (
          <BlurView
            intensity={26}
            tint="light"
            style={[StyleSheet.absoluteFill, { borderRadius: 35, overflow: 'hidden', borderWidth: 1, borderColor: theme.colors.border }]}
          />
        ),
      })}
    >
      <Tab.Screen name="NurseHome" component={NurseDashboardScreen} />
      <Tab.Screen name="NurseQueue" component={NurseQueueScreen} />
      <Tab.Screen name="NurseCheckIn" component={NurseCheckInScreen} />
      <Tab.Screen name="NurseVitals" component={VitalsScreen} />
      <Tab.Screen name="NurseAccount" component={NurseProfileScreen} />
    </Tab.Navigator>
  );
}

// ─── Admin Tab Navigator ──────────────────────────────────────────────────────
function AdminTabs() {
  const theme = useTheme();
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        ...tabOpts,
        tabBarIcon: ({ focused, color, size }) => {
          const icons: Record<string, [string, string]> = {
            AdminHome: ['grid', 'grid-outline'],
            AdminStaff: ['people', 'people-outline'],
            AdminDepts: ['business', 'business-outline'],
            AdminAnalytics: ['bar-chart', 'bar-chart-outline'],
            AdminAccount: ['person', 'person-outline'],
          };
          const [active, inactive] = icons[route.name] || ['ellipse', 'ellipse-outline'];
          return (
            <View style={focused ? styles.activeTab : null}>
              <Ionicons name={(focused ? active : inactive) as any} size={size} color={color} />
            </View>
          );
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.text.low,
        tabBarStyle: styles.tabBar,
        tabBarBackground: () => (
          <BlurView
            intensity={26}
            tint="light"
            style={[StyleSheet.absoluteFill, { borderRadius: 35, overflow: 'hidden', borderWidth: 1, borderColor: theme.colors.border }]}
          />
        ),
      })}
    >
      <Tab.Screen name="AdminHome" component={AdminDashboardScreen} />
      <Tab.Screen name="AdminStaff" component={StaffManagementScreen} />
      <Tab.Screen name="AdminDepts" component={DepartmentsScreen} />
      <Tab.Screen name="AdminAnalytics" component={AdminAnalyticsScreen} />
      <Tab.Screen name="AdminAccount" component={AdminProfileScreen} />
    </Tab.Navigator>
  );
}

// ─── Role-Based Stack Navigator ───────────────────────────────────────────────
export default function RoleBasedNavigator() {
  const { user } = useAuth();
  const role = user?.role ?? 'patient';

  const initialRoute =
    role === 'doctor' ? 'DoctorMain' :
    role === 'nurse'  ? 'NurseMain'  :
    role === 'admin'  ? 'AdminMain'  : 'PatientMain';

  return (
    <Stack.Navigator initialRouteName={initialRoute} screenOptions={{ headerShown: false }}>
      {/* Patient Stack */}
      <Stack.Screen name="PatientMain" component={PatientTabs} />
      <Stack.Screen name="Navigation" component={NavigationScreen} />
      <Stack.Screen name="Emergency" component={EmergencyScreen} />
      <Stack.Screen name="VoiceAssistant" component={VoiceAssistantScreen} />
      <Stack.Screen name="Settings" component={SettingsScreen} />
      <Stack.Screen name="Telehealth" component={TelehealthScreen} />
      <Stack.Screen name="Pharmacy" component={PharmacyScreen} />
      <Stack.Screen name="Billing" component={BillingScreen} />

      {/* Doctor Stack */}
      <Stack.Screen name="DoctorMain" component={DoctorTabs} />
      <Stack.Screen name="PatientDetails" component={PatientDetailsScreen} />
      <Stack.Screen name="WritePrescription" component={PrescriptionScreen} />
      <Stack.Screen name="DoctorEmergency" component={DoctorEmergencyScreen} />

      {/* Nurse Stack */}
      <Stack.Screen name="NurseMain" component={NurseTabs} />
      <Stack.Screen name="NurseEmergency" component={NurseEmergencyScreen} />

      {/* Admin Stack */}
      <Stack.Screen name="AdminMain" component={AdminTabs} />
      <Stack.Screen name="Inventory" component={InventoryScreen} />
      <Stack.Screen name="AuditLogs" component={AuditLogsScreen} />
    </Stack.Navigator>
  );
}

const styles = StyleSheet.create({
  activeTab: { backgroundColor: '#D8E2DC', padding: 10, borderRadius: 20 },
  tabBar: {
    position: 'absolute',
    bottom: Platform.OS === 'ios' ? 30 : 20,
    left: 20,
    right: 20,
    height: 70,
    borderRadius: 35,
    backgroundColor: 'rgba(255,255,255,0.78)',
    borderTopWidth: 0,
    elevation: 0,
    shadowColor: 'rgba(0,0,0,0.05)',
    shadowOpacity: 0.12,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
  },
});
