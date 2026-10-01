import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';

import {
  NavioraAvatar,
  NavioraBadge,
  NavioraButton,
  NavioraCard,
  NavioraHeader,
  NavioraText,
} from '../../components/common/AtomicComponents';
import { useTheme } from '../../context/ThemeContext';
import { apiService } from '../../services/api';

interface StaffMember {
  id: number;
  email: string;
  phone: string | null;
  role: string;
  is_active: boolean;
}

const StaffManagementScreen = () => {
  const theme = useTheme();
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  const loadStaff = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.get<StaffMember[]>('/admin/staff');
      if (!mounted.current) return;
      if (result.error || !result.data) {
        setError(result.error || 'Staff data is unavailable.');
        return;
      }
      setStaff(Array.isArray(result.data) ? result.data : []);
    } catch (loadError) {
      if (mounted.current) {
        setError(loadError instanceof Error ? loadError.message : 'Unable to load staff.');
      }
    } finally {
      if (mounted.current) setLoading(false);
    }
  };

  useEffect(() => {
    mounted.current = true;
    void loadStaff();
    return () => {
      mounted.current = false;
    };
  }, []);

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <NavioraHeader title="Staff Management" subtitle="Staff roles and account status" />

        {loading ? (
          <ActivityIndicator color={theme.colors.primary} style={{ marginTop: 28 }} />
        ) : error ? (
          <View style={styles.message}>
            <NavioraText variant="body" color="error">{error}</NavioraText>
            <TouchableOpacity onPress={() => void loadStaff()}>
              <NavioraText variant="label" color="primary" style={{ marginTop: 10 }}>Try again</NavioraText>
            </TouchableOpacity>
          </View>
        ) : staff.length > 0 ? (
          staff.map((member) => (
            <NavioraCard key={member.id} style={styles.card}>
              <View style={styles.row}>
                <NavioraAvatar initials={member.email.split('@')[0].slice(0, 2).toUpperCase()} size={42} online={member.is_active} />
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <NavioraText variant="body" style={{ fontWeight: '700' }}>{member.email}</NavioraText>
                  <NavioraText variant="caption" color="secondary">
                    {member.role}{member.phone ? ` • ${member.phone}` : ''}
                  </NavioraText>
                </View>
                <NavioraBadge label={member.is_active ? 'Active' : 'Inactive'} tone={member.is_active ? 'success' : 'danger'} />
              </View>
            </NavioraCard>
          ))
        ) : (
          <NavioraText variant="body" color="secondary" style={styles.message}>No staff members found.</NavioraText>
        )}

        <NavioraButton title="Add Staff" icon="person-add-outline" style={{ marginTop: 20 }} />
      </ScrollView>
    </SafeAreaView>
  );
};

export default StaffManagementScreen;

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 30 },
  card: { marginTop: 12 },
  row: { flexDirection: 'row', alignItems: 'center' },
  message: { marginTop: 28, alignItems: 'center' },
});
