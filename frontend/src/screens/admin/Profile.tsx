import React from 'react';
import { SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';

import {
  NavioraAvatar,
  NavioraBadge,
  NavioraCard,
  NavioraHeader,
  NavioraListItem,
  NavioraText,
} from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';

const AdminProfileScreen = () => {
  const theme = useTheme();
  const { user } = useAuth();

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <NavioraHeader title="Admin Profile" subtitle="System access and admin role" />
        <NavioraCard style={styles.card}>
          <View style={styles.row}>
            <NavioraAvatar initials={(user?.name || 'Admin').slice(0, 2).toUpperCase()} size={68} online />
            <View style={{ marginLeft: 14, flex: 1 }}>
              <NavioraText variant="h3">{user?.name || 'Administrator'}</NavioraText>
              <NavioraText variant="caption" color="secondary">{user?.email || 'Account email unavailable'}</NavioraText>
              <NavioraBadge label="System Access" tone="success" />
            </View>
          </View>
        </NavioraCard>

        <NavioraListItem icon="settings-outline" title="System settings" subtitle="Hospital policies and security" />
        <NavioraListItem icon="shield-checkmark-outline" title="Security center" subtitle="HIPAA and audit compliance" />
        <NavioraListItem icon="log-out-outline" title="Sign out" subtitle="Terminate active session" />
      </ScrollView>
    </SafeAreaView>
  );
};

export default AdminProfileScreen;

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 30 },
  card: { marginTop: 12 },
  row: { flexDirection: 'row', alignItems: 'center' },
});
