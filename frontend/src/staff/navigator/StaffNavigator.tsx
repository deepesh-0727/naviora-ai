import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import type { ComponentProps } from 'react';

import { RoleGuard } from '../../shared/guards/RoleGuard';
import { useRole } from '../../shared/contexts/RoleContext';
import type { Role } from '../../shared/types/roles';
import StaffModuleScreen from './StaffModuleScreen';
import DoctorDashboard from '../screens/DoctorDashboard';
import DoctorQueue from '../screens/DoctorQueue';
import PatientDetail from '../screens/PatientDetail';

type TabIconName = ComponentProps<typeof Ionicons>['name'];
type TabDefinition = { name: string; title: string; endpoint: string; icon: TabIconName };
const Tab = createBottomTabNavigator();

const STAFF_TABS: Record<Exclude<Role, 'patient' | 'admin' | 'super_admin'>, TabDefinition[]> = {
  doctor: [
    { name: 'Home', title: 'Doctor Dashboard', endpoint: 'GET /staff/doctor/schedule', icon: 'grid-outline' },
    { name: 'Queue', title: 'Doctor Queue', endpoint: 'GET /staff/doctor/queue', icon: 'list-outline' },
    { name: 'Emergency', title: 'Emergency', endpoint: 'GET /staff/emergency/active', icon: 'alert-circle-outline' },
    { name: 'Notifications', title: 'Notifications', endpoint: 'GET /staff/notifications', icon: 'notifications-outline' },
    { name: 'Profile', title: 'Profile', endpoint: 'GET /staff/profile', icon: 'person-outline' },
  ],
  nurse: [
    { name: 'Home', title: 'Nurse Dashboard', endpoint: 'GET /staff/nurse/ward', icon: 'grid-outline' },
    { name: 'Patients', title: 'Patients', endpoint: 'GET /staff/nurse/patients', icon: 'people-outline' },
    { name: 'Emergency', title: 'Emergency', endpoint: 'GET /staff/emergency/active', icon: 'alert-circle-outline' },
    { name: 'Notifications', title: 'Notifications', endpoint: 'GET /staff/notifications', icon: 'notifications-outline' },
    { name: 'Profile', title: 'Profile', endpoint: 'GET /staff/profile', icon: 'person-outline' },
  ],
  front_desk: [
    { name: 'Home', title: 'Front Desk', endpoint: 'GET /staff/front-desk/dashboard', icon: 'grid-outline' },
    { name: 'Queue', title: 'Queue', endpoint: 'GET /staff/queue', icon: 'list-outline' },
    { name: 'Bookings', title: 'Bookings', endpoint: 'GET /staff/appointments', icon: 'calendar-outline' },
    { name: 'Notifications', title: 'Notifications', endpoint: 'GET /staff/notifications', icon: 'notifications-outline' },
    { name: 'Profile', title: 'Profile', endpoint: 'GET /staff/profile', icon: 'person-outline' },
  ],
  pharmacy: [
    { name: 'Home', title: 'Pharmacy', endpoint: 'GET /staff/pharmacy/prescriptions', icon: 'grid-outline' },
    { name: 'Inventory', title: 'Inventory', endpoint: 'GET /staff/pharmacy/inventory', icon: 'medkit-outline' },
    { name: 'Notifications', title: 'Notifications', endpoint: 'GET /staff/notifications', icon: 'notifications-outline' },
    { name: 'Profile', title: 'Profile', endpoint: 'GET /staff/profile', icon: 'person-outline' },
  ],
  facilities: [
    { name: 'Home', title: 'Facilities', endpoint: 'GET /staff/facilities/beds', icon: 'grid-outline' },
    { name: 'Beds', title: 'Beds', endpoint: 'GET /staff/facilities/beds', icon: 'bed-outline' },
    { name: 'Equipment', title: 'Equipment', endpoint: 'GET /staff/facilities/equipment', icon: 'construct-outline' },
    { name: 'Notifications', title: 'Notifications', endpoint: 'GET /staff/notifications', icon: 'notifications-outline' },
    { name: 'Profile', title: 'Profile', endpoint: 'GET /staff/profile', icon: 'person-outline' },
  ],
  emergency: [
    { name: 'Home', title: 'Emergency Console', endpoint: 'GET /staff/emergency/active', icon: 'grid-outline' },
    { name: 'Active', title: 'Active Incidents', endpoint: 'GET /staff/emergency/active', icon: 'alert-circle-outline' },
    { name: 'Map', title: 'Incident Locations', endpoint: 'GET /staff/emergency/active', icon: 'navigate-outline' },
    { name: 'Notifications', title: 'Notifications', endpoint: 'GET /staff/notifications', icon: 'notifications-outline' },
    { name: 'Profile', title: 'Profile', endpoint: 'GET /staff/profile', icon: 'person-outline' },
  ],
};

function RoleTabs({ role }: { role: Exclude<Role, 'patient' | 'admin' | 'super_admin'> }) {
  const allowedRoles: Role[] = [role];
  return (
    <RoleGuard allow={allowedRoles}>
      <Tab.Navigator
        screenOptions={({ route }) => {
          const definition = STAFF_TABS[role].find((item) => item.name === route.name);
          return {
            headerShown: false,
            tabBarIcon: ({ color, size }) => <Ionicons name={definition?.icon ?? 'ellipse-outline'} size={size} color={color} />,
            tabBarActiveTintColor: '#1D8A6C',
            tabBarInactiveTintColor: '#8899AA',
          };
        }}
      >
        {STAFF_TABS[role].map((tab) => (
          <Tab.Screen key={tab.name} name={tab.name} options={{ title: tab.name }}>
            {() => {
              if (role === 'doctor' && tab.name === 'Home') return <DoctorDashboard />;
              if (role === 'doctor' && tab.name === 'Queue') return <DoctorQueue />;
              if (role === 'doctor' && tab.name === 'Patients') return <PatientDetail />;
              return <StaffModuleScreen title={tab.title} endpoint={tab.endpoint} />;
            }}
          </Tab.Screen>
        ))}
        {role === 'doctor' ? (
          <Tab.Screen
            name="PatientDetail"
            component={PatientDetail}
            options={{ tabBarButton: () => null, title: 'Patient Detail' }}
          />
        ) : null}
      </Tab.Navigator>
    </RoleGuard>
  );
}

export function DoctorTabs() { return <RoleTabs role="doctor" />; }
export function NurseTabs() { return <RoleTabs role="nurse" />; }
export function FrontDeskTabs() { return <RoleTabs role="front_desk" />; }
export function PharmacyTabs() { return <RoleTabs role="pharmacy" />; }
export function FacilitiesTabs() { return <RoleTabs role="facilities" />; }
export function EmergencyTabs() { return <RoleTabs role="emergency" />; }

export default function StaffNavigator() {
  const { role } = useRole();
  switch (role) {
    case 'doctor': return <DoctorTabs />;
    case 'nurse': return <NurseTabs />;
    case 'front_desk': return <FrontDeskTabs />;
    case 'pharmacy': return <PharmacyTabs />;
    case 'facilities': return <FacilitiesTabs />;
    case 'emergency': return <EmergencyTabs />;
    default: return <StaffModuleScreen title="Staff access required" endpoint="Authenticated staff session" />;
  }
}
