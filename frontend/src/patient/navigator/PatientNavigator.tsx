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
      <Text style={styles.sosText}>SOS</Text>
    </TouchableOpacity>
  );
}

// ─── Tab icon helper ──────────────────────────────────────────────────────────

const TAB_ICONS: Record<string, string> = {
  Home: '🏠',
  Appointments: '📅',
  Voice: '🎙',
  Notifications: '🔔',
  Profile: '👤',
};

// ─── Bottom Tabs ──────────────────────────────────────────────────────────────

function PatientTabs() {
  return (
    <View style={{ flex: 1 }}>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarIcon: ({ focused }) => (
            <Text style={{ fontSize: 18, opacity: focused ? 1 : 0.5 }}>
              {TAB_ICONS[route.name] ?? '•'}
            </Text>
          ),
          tabBarActiveTintColor: '#1D8A6C',
          tabBarInactiveTintColor: '#8899AA',
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
    bottom: 72,
    right: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#D94A4A',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#D94A4A',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.45,
    shadowRadius: 8,
    elevation: 8,
    zIndex: 999,
  },
  sosText: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 13,
    letterSpacing: 0.5,
  },
  tabBar: {
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#E5EAF0',
    paddingTop: 4,
    height: 64,
  },
  tabLabel: {
    fontSize: 11,
    marginTop: 2,
  },
});
