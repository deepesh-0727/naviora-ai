import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { View, StyleSheet, Platform } from 'react-native';
import 'react-native-gesture-handler';

// Font Loading
import {
  useFonts,
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Inter_800ExtraBold,
} from '@expo-google-fonts/inter';

// Enterprise Contexts
import { ThemeProvider, useTheme } from './src/context/ThemeContext';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { ProfileProvider } from './src/context/ProfileContext';
import { QueueProvider } from './src/context/QueueContext';
import { AlertProvider } from './src/context/AlertContext';
import { LanguageProvider } from './src/context/LanguageContext';

// Import Components
import { GlobalAlert } from './src/components/common/GlobalAlert';

// Import Screens
import SplashScreen from './src/screens/Splash';
import LoginScreen from './src/screens/Login';
import OTPScreen from './src/screens/OTP';
import DashboardScreen from './src/screens/Dashboard';
import VoiceAssistantScreen from './src/screens/VoiceAssistant';
import AppointmentScreen from './src/screens/Appointment';
import RegistrationScreen from './src/screens/Registration';
import NavigationScreen from './src/screens/Navigation';
import EmergencyScreen from './src/screens/Emergency';
import NotificationsScreen from './src/screens/Notifications';
import SettingsScreen from './src/screens/Settings';
import ProfileScreen from './src/screens/Profile';
import TelehealthScreen from './src/screens/Telehealth';
import PharmacyScreen from './src/screens/Pharmacy';
import BillingScreen from './src/screens/BillingScreen';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();
const RoleStack = createStackNavigator();

function RoleBasedHome() {
  const { user } = useAuth();

  if (user?.role === 'doctor') {
    return (
      <RoleStack.Navigator screenOptions={{ headerShown: false }}>
        <RoleStack.Screen name="DoctorDashboard" component={require('./src/screens/doctor/Dashboard').default} />
        <RoleStack.Screen name="DocQueue" component={require('./src/screens/doctor/Queue').default} />
        <RoleStack.Screen name="PatientDetails" component={require('./src/screens/doctor/PatientDetails').default} />
        <RoleStack.Screen name="WritePrescription" component={require('./src/screens/doctor/Prescription').default} />
        <RoleStack.Screen name="DoctorSchedule" component={require('./src/screens/doctor/Schedule').default} />
        <RoleStack.Screen name="DoctorEmergency" component={require('./src/screens/doctor/EmergencyResponse').default} />
        <RoleStack.Screen name="DocAnalytics" component={require('./src/screens/doctor/Analytics').default} />
        <RoleStack.Screen name="DoctorProfile" component={require('./src/screens/doctor/Profile').default} />
      </RoleStack.Navigator>
    );
  }

  if (user?.role === 'nurse' || user?.role === 'staff') {
    return (
      <RoleStack.Navigator screenOptions={{ headerShown: false }}>
        <RoleStack.Screen name="NurseDashboard" component={require('./src/screens/nurse/Dashboard').default} />
        <RoleStack.Screen name="NurseCheckIn" component={require('./src/screens/nurse/CheckIn').default} />
        <RoleStack.Screen name="NurseVitals" component={require('./src/screens/nurse/Vitals').default} />
        <RoleStack.Screen name="NurseQueue" component={require('./src/screens/nurse/Queue').default} />
        <RoleStack.Screen name="NurseEmergency" component={require('./src/screens/nurse/Emergency').default} />
        <RoleStack.Screen name="NurseProfile" component={require('./src/screens/nurse/Profile').default} />
      </RoleStack.Navigator>
    );
  }

  if (user?.role === 'admin') {
    return (
      <RoleStack.Navigator screenOptions={{ headerShown: false }}>
        <RoleStack.Screen name="AdminDashboard" component={require('./src/screens/admin/Dashboard').default} />
        <RoleStack.Screen name="StaffManagement" component={require('./src/screens/admin/StaffManagement').default} />
        <RoleStack.Screen name="Departments" component={require('./src/screens/admin/Departments').default} />
        <RoleStack.Screen name="Inventory" component={require('./src/screens/admin/Inventory').default} />
        <RoleStack.Screen name="AdminAnalytics" component={require('./src/screens/admin/Analytics').default} />
        <RoleStack.Screen name="AuditLogs" component={require('./src/screens/admin/AuditLogs').default} />
        <RoleStack.Screen name="AdminProfile" component={require('./src/screens/admin/Profile').default} />
      </RoleStack.Navigator>
    );
  }

  return <MainTabNavigator />;
}

function MainTabNavigator() {
  const theme = useTheme();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: any;
          if (route.name === 'Home') iconName = focused ? 'home' : 'home-outline';
          else if (route.name === 'Voice') iconName = focused ? 'mic' : 'mic-outline';
          else if (route.name === 'Calendar') iconName = focused ? 'calendar' : 'calendar-outline';
          else if (route.name === 'Alerts') iconName = focused ? 'notifications' : 'notifications-outline';
          else if (route.name === 'Account') iconName = focused ? 'person' : 'person-outline';

          return (
            <View style={focused ? styles.activeTab : null}>
              <Ionicons name={iconName} size={size} color={color} />
            </View>
          );
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.text.low,
        tabBarStyle: {
          position: 'absolute',
          bottom: Platform.OS === 'ios' ? 30 : 20,
          left: 20,
          right: 20,
          height: 70,
          borderRadius: 35,
          backgroundColor: 'rgba(255,255,255,0.78)',
          borderTopWidth: 0,
          elevation: 0,
          shadowColor: theme.colors.shadow,
          shadowOpacity: 0.12,
          shadowRadius: 12,
          shadowOffset: { width: 0, height: 6 },
        },
        tabBarBackground: () => (
          <BlurView
            intensity={26}
            tint="light"
            style={[StyleSheet.absoluteFill, { borderRadius: 35, overflow: 'hidden', borderWidth: 1, borderColor: theme.colors.border }]}
          />
        ),
        headerShown: false,
        tabBarShowLabel: false,
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

export default function App() {
  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    Inter_800ExtraBold,
  });

  if (!fontsLoaded) {
    return null; // Or a very simple splash fallback if fonts take time
  }

  return (
    <LanguageProvider>
      <ThemeProvider>
        <AuthProvider>
        <AlertProvider>
          <ProfileProvider>
            <QueueProvider>
              <NavigationContainer>
                <GlobalAlert />
                <Stack.Navigator
                  initialRouteName="Splash"
                  screenOptions={{
                    headerStyle: {
                      backgroundColor: '#F7F9F5',
                      borderBottomWidth: 1,
                      borderBottomColor: 'rgba(58, 90, 64, 0.12)',
                    },
                    headerTintColor: '#1A1A1A',
                    headerTitleStyle: {
                      fontWeight: 'bold',
                      fontFamily: 'Inter_700Bold',
                    },
                    cardStyle: { backgroundColor: '#FAFAF7' },
                    headerBackTitleVisible: false,
                  }}
                >
                  <Stack.Screen name="Splash" component={SplashScreen} options={{ headerShown: false }} />
                  <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
                  <Stack.Screen name="Registration" component={RegistrationScreen} options={{ headerShown: false }} />
                  <Stack.Screen name="Register" component={RegistrationScreen} options={{ headerShown: false }} />
                  <Stack.Screen name="OTP" component={OTPScreen} options={{ title: 'Verify OTP' }} />
                  <Stack.Screen name="Main" component={RoleBasedHome} options={{ headerShown: false }} />
                  <Stack.Screen name="VoiceAssistant" component={VoiceAssistantScreen} options={{ headerShown: false }} />
                  <Stack.Screen name="Emergency" component={EmergencyScreen} options={{ headerShown: false }} />
                  <Stack.Screen name="Navigation" component={NavigationScreen} options={{ title: 'Hospital Navigation' }} />
                  <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: 'Settings' }} />
                  <Stack.Screen name="Telehealth" component={TelehealthScreen} options={{ headerShown: false }} />
                  <Stack.Screen name="Pharmacy" component={PharmacyScreen} options={{ title: 'Pharmacy' }} />
                  <Stack.Screen name="Billing" component={BillingScreen} options={{ title: 'My Bills', headerShown: false }} />
                </Stack.Navigator>
              </NavigationContainer>
            </QueueProvider>
          </ProfileProvider>
        </AlertProvider>
        </AuthProvider>
      </ThemeProvider>
    </LanguageProvider>
  );
}

const styles = StyleSheet.create({
  activeTab: {
    backgroundColor: '#D8E2DC',
    padding: 10,
    borderRadius: 20,
  },
});
