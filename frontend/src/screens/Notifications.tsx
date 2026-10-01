import React, { useEffect, useState, useCallback } from 'react';
import { StyleSheet, View, ScrollView, TouchableOpacity, SafeAreaView, RefreshControl, ActivityIndicator, Dimensions } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInUp } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { NavioraText, GlassCard, StatusBadge } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const { width } = Dimensions.get('window');

interface NotificationItem {
  id: number;
  title: string;
  message: string;
  type: string;
  created_at: string;
  is_read: boolean;
}

export default function NotificationsScreen({ navigation }: any) {
  const theme = useTheme();
  const [activeFilter, setActiveFilter] = useState('All');
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(false);

  const { lastMessage } = useWebSocket();

  const fetchNotifications = useCallback(async () => {
    const result = await apiService.get<any>('/notifications');
    if (result.data) {
      const list = Array.isArray(result.data) ? result.data : (result.data.notifications || []);
      setNotifications(list);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchNotifications().finally(() => setLoading(false));
  }, [fetchNotifications]);

  useEffect(() => {
    if (lastMessage && (lastMessage.type === 'notification' || lastMessage.type === 'emergency_alert')) {
      const newNotif: NotificationItem = {
        id: Date.now(),
        title: lastMessage.title || 'New Update',
        message: lastMessage.message || lastMessage.content || '',
        type: lastMessage.type === 'emergency_alert' ? 'emergency' : 'queue',
        created_at: new Date().toISOString(),
        is_read: false
      };
      setNotifications(prev => [newNotif, ...prev]);
    }
  }, [lastMessage]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchNotifications();
    setRefreshing(false);
  };

  const markAllRead = async () => {
    await apiService.put('/notifications/read-all', {});
    setNotifications(current => current.map(item => ({ ...item, is_read: true })));
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'emergency': return { name: 'flash', color: theme.colors.error };
      case 'queue': return { name: 'people', color: theme.colors.primary };
      case 'appointment': return { name: 'calendar', color: theme.colors.accent };
      default: return { name: 'notifications', color: theme.colors.purple };
    }
  };

  const filteredNotifications = notifications.filter(item => {
    if (activeFilter === 'Unread') return !item.is_read;
    if (activeFilter === 'Read') return item.is_read;
    return true;
  });

  const FilterTab = ({ name }: { name: string }) => (
    <TouchableOpacity
      onPress={() => setActiveFilter(name)}
      style={[styles.filterTab, activeFilter === name && { backgroundColor: theme.colors.primary }]}
    >
      <NavioraText type="xs" style={{ color: activeFilter === name ? '#FFF' : theme.colors.text.low, fontWeight: '700' }}>
        {name.toUpperCase()}
      </NavioraText>
    </TouchableOpacity>
  );

  const NotificationCard = ({ item, index }: { item: NotificationItem; index: number }) => {
    const icon = getIcon(item.type);
    return (
      <Animated.View entering={FadeInUp.delay(index * 100)}>
        <GlassCard style={[styles.card, !item.is_read && { borderLeftWidth: 4, borderLeftColor: theme.colors.primary }]}>
          <View style={styles.cardRow}>
            <View style={[styles.iconCircle, { backgroundColor: icon.color + '20' }]}>
              <Ionicons name={icon.name as any} size={24} color={icon.color} />
            </View>
            <View style={{ flex: 1, marginLeft: 16 }}>
              <View style={styles.titleRow}>
                <NavioraText type="h3">{item.title}</NavioraText>
                {!item.is_read && <View style={[styles.unreadDot, { backgroundColor: theme.colors.primary }]} />}
              </View>
              <NavioraText type="body" color="low" style={{ marginTop: 4 }}>{item.message}</NavioraText>
              <NavioraText type="xs" color="low" style={{ marginTop: 8 }}>
                {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </NavioraText>
            </View>
          </View>
        </GlassCard>
      </Animated.View>
    );
  };

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.header}>
          <View>
            <NavioraText type="h2">Notifications</NavioraText>
            <NavioraText type="xs" color="low">{notifications.filter(n => !n.is_read).length} new updates</NavioraText>
          </View>
          <TouchableOpacity style={styles.clearBtn} onPress={markAllRead}>
            <NavioraText type="label" color="primary">Mark all read</NavioraText>
          </TouchableOpacity>
        </View>

        <View style={styles.filterContainer}>
          <FilterTab name="All" />
          <FilterTab name="Unread" />
          <FilterTab name="Read" />
        </View>

        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary} />}
        >
          {loading && !refreshing ? (
            <ActivityIndicator size="large" color={theme.colors.primary} style={{ marginTop: 40 }} />
          ) : filteredNotifications.length > 0 ? (
            filteredNotifications.map((n, idx) => <NotificationCard key={n.id} item={n} index={idx} />)
          ) : (
            <View style={styles.emptyContainer}>
              <Ionicons name="mail-open-outline" size={80} color={theme.colors.glass.border} />
              <NavioraText type="h3" color="low" style={{ marginTop: 24 }}>Everything caught up!</NavioraText>
              <NavioraText type="body" color="low" align="center" style={{ marginTop: 8 }}>
                You don't have any notifications at the moment.
              </NavioraText>
            </View>
          )}
          <View style={{ height: 100 }} />
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', padding: 24 },
  clearBtn: { padding: 4 },
  filterContainer: { flexDirection: 'row', paddingHorizontal: 24, gap: 12, marginBottom: 20 },
  filterTab: { paddingHorizontal: 20, paddingVertical: 8, borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.05)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.05)' },
  scrollContent: { paddingHorizontal: 24 },
  card: { padding: 16, marginBottom: 12 },
  cardRow: { flexDirection: 'row', alignItems: 'flex-start' },
  iconCircle: { width: 52, height: 52, borderRadius: 26, justifyContent: 'center', alignItems: 'center' },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  unreadDot: { width: 10, height: 10, borderRadius: 5 },
  emptyContainer: { alignItems: 'center', marginTop: 100, paddingHorizontal: 40 },
});
