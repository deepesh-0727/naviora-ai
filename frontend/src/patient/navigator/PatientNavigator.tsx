import React from 'react';
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../../shared/theme';

// Screens – resolved lazily after Batch 2 & 3 move/create them
// For now we forward-reference them from ../../screens (old location)
// Batch 2 will create patient/screens copies; imports updated there.
import DashboardScreen from '../screens/Dashboard';
import AppointmentScreen from '../screens/Appointment';
import VoiceAssistantScreen from '../screens/VoiceAssistant';
import NotificationsScreen from '../screens/Notifications';
import ProfileScreen from '../screens/Profile';
import NavigationScreen from '../screens/Navigation';
import EmergencyScreen from '../screens/Emergency';
import SettingsScreen from '../screens/Settings';
import FeedbackScreen from '../screens/Feedback';

// ─── Route param lists ────────────────────────────────────────────────────────

export type PatientRootParamList = {
  PatientTabs: undefined;
  Navigation: undefined;
  Emergency: undefined;
  Settings: undefined;
  Feedback: { appointmentId: number };
};

export type PatientTabParamList = {
  Home: undefined;
  Appointments: undefined;
  Voice: undefined;
  Notifications: undefined;
  Profile: undefined;
};

// ─── Navigators ───────────────────────────────────────────────────────────────

const Tab = createBottomTabNavigator<PatientTabParamList>();
const Stack = createStackNavigator<PatientRootParamList>();

// ─── Floating SOS Button ─────────────────────────────────────────────────────

function SOSButton() {
  const navigation = useNavigation<StackNavigationProp<PatientRootParamList>>();
  return (
    <TouchableOpacity
      accessibilityLabel="Emergency SOS"
      accessibilityRole="button"
      style={styles.sos}
      onPress={() => navigation.navigate('Emergency')}
    >
      <Ionicons name="alert-circle" size={21} color={COLORS.white} />
      <Text style={styles.sosText}>SOS Emergency</Text>
    </TouchableOpacity>
  );
}

// ─── Tab icon helper ──────────────────────────────────────────────────────────

const TAB_ICONS: Record<string, { active: keyof typeof Ionicons.glyphMap; inactive: keyof typeof Ionicons.glyphMap }> = {
  Home: { active: 'home', inactive: 'home-outline' },
  Appointments: { active: 'calendar', inactive: 'calendar-outline' },
  Voice: { active: 'mic', inactive: 'mic-outline' },
  Notifications: { active: 'notifications', inactive: 'notifications-outline' },
  Profile: { active: 'person', inactive: 'person-outline' },
};

// ─── Bottom Tabs ──────────────────────────────────────────────────────────────

function PatientTabs() {
  return (
    <View style={{ flex: 1, backgroundColor: COLORS.background }}>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarIcon: ({ focused, color }) => <Ionicons name={focused ? TAB_ICONS[route.name].active : TAB_ICONS[route.name].inactive} size={22} color={color} />,
          tabBarActiveTintColor: COLORS.primary,
          tabBarInactiveTintColor: COLORS.textMuted,
          tabBarStyle: styles.tabBar,
          tabBarLabelStyle: styles.tabLabel,
        })}
      >
        <Tab.Screen name="Home" component={DashboardScreen} />
        <Tab.Screen name="Appointments" component={AppointmentScreen} />
        <Tab.Screen name="Voice" component={VoiceAssistantScreen} />
        <Tab.Screen name="Notifications" component={NotificationsScreen} />
        <Tab.Screen name="Profile" component={ProfileScreen} />
      </Tab.Navigator>
      {/* Floating SOS rendered above tabs */}
      <SOSButton />
    </View>
  );
}

// ─── Root Stack ───────────────────────────────────────────────────────────────

export default function PatientNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="PatientTabs" component={PatientTabs} />
      <Stack.Screen name="Navigation" component={NavigationScreen} />
      <Stack.Screen name="Emergency" component={EmergencyScreen} />
      <Stack.Screen name="Settings" component={SettingsScreen} />
      <Stack.Screen name="Feedback" component={FeedbackScreen} />
    </Stack.Navigator>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  sos: {
    position: 'absolute',
    bottom: 82,
    right: 20,
    minWidth: 176,
    height: 58,
    paddingHorizontal: 18,
    borderRadius: 999,
    backgroundColor: COLORS.danger,
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: COLORS.danger,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.24,
    shadowRadius: 8,
    elevation: 8,
    zIndex: 999,
  },
  sosText: {
    color: COLORS.white,
    fontWeight: '800',
    fontSize: 13,
    letterSpacing: 0.5,
  },
  tabBar: {
    backgroundColor: COLORS.white,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    paddingTop: 7,
    height: 68,
  },
  tabLabel: {
    fontSize: 11,
    marginTop: 2,
  },
});
