import React, { useState, useEffect } from 'react';
import { StyleSheet, View, TouchableOpacity, SafeAreaView, Dimensions, ScrollView, TextInput, ActivityIndicator } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeIn } from 'react-native-reanimated';
import Svg, { Rect, Path, Circle } from 'react-native-svg';

import { useTheme } from '../context/ThemeContext';
import { NavioraText, GlassCard, GradientButton } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';

const { width, height } = Dimensions.get('window');

export default function NavigationScreen({ navigation }: any) {
  const theme = useTheme();
  const [activeFloor, setActiveFloor] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [departments, setDepartments] = useState<any[]>([]);

  useEffect(() => {
    setLoading(true);
    apiService.get<any>('/navigation/departments').then(res => {
      setLoading(false);
      if (res.data) {
        setDepartments(Array.isArray(res.data) ? res.data : (res.data.departments || []));
      }
    }).catch(() => setLoading(false));
  }, []);

  const filteredDepartments = departments.filter((d: any) =>
    (d.name || d.department_name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const FloorBtn = ({ floor }: { floor: any }) => (
    <TouchableOpacity
      onPress={() => setActiveFloor(floor === 'G' ? 0 : floor)}
      style={[
        styles.floorBtn,
        { backgroundColor: (activeFloor === floor || (floor === 'G' && activeFloor === 0)) ? theme.colors.primary : theme.colors.glass.bg, borderColor: theme.colors.glass.border }
      ]}
    >
      <NavioraText type="label" style={{ color: '#FFF' }}>{floor}</NavioraText>
    </TouchableOpacity>
  );

  const DestinationItem = ({ name, icon, floor, color }: any) => (
    <TouchableOpacity style={styles.destItem}>
      <View style={[styles.destIcon, { backgroundColor: color + '20' }]}>
        <Ionicons name={icon || "medical"} size={24} color={color} />
      </View>
      <View style={{ flex: 1, marginLeft: 16 }}>
        <NavioraText type="h3">{name}</NavioraText>
        <NavioraText type="xs" color="low">Floor {floor ?? 1}</NavioraText>
      </View>
      <Ionicons name="chevron-forward" size={20} color={theme.colors.text.low} />
    </TouchableOpacity>
  );

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={28} color="#FFF" />
          </TouchableOpacity>
          <NavioraText type="h2" style={{ marginLeft: 12, flex: 1 }}>Find Your Way</NavioraText>
          <TouchableOpacity style={styles.iconBtn}>
            <Ionicons name="mic-outline" size={24} color="#FFF" />
          </TouchableOpacity>
        </View>

        <View style={styles.searchContainer}>
          <GlassCard style={styles.searchBar}>
            <Ionicons name="search" size={20} color={theme.colors.text.low} />
            <TextInput
              placeholder="Search departments..."
              placeholderTextColor={theme.colors.text.low}
              value={searchQuery}
              onChangeText={setSearchQuery}
              style={[styles.searchInput, { color: theme.colors.text.high }]}
            />
          </GlassCard>
        </View>

        <View style={styles.mapArea}>
          <Animated.View entering={FadeIn} style={[styles.mapMock, { backgroundColor: theme.colors.glass.bg, borderColor: theme.colors.glass.border }]}>
            
            <Svg height="100%" width="100%" viewBox="0 0 400 300">
              <Rect width="400" height="300" fill="transparent" />
              <Rect x="20" y="20" width="100" height="80" fill={theme.colors.surfaceVariant} stroke={theme.colors.glass.border} strokeWidth="2" />
              <Rect x="140" y="20" width="100" height="80" fill={theme.colors.surfaceVariant} stroke={theme.colors.glass.border} strokeWidth="2" />
              <Rect x="260" y="20" width="120" height="120" fill={theme.colors.surfaceVariant} stroke={theme.colors.glass.border} strokeWidth="2" />
              
              <Rect x="20" y="200" width="150" height="80" fill={theme.colors.surfaceVariant} stroke={theme.colors.glass.border} strokeWidth="2" />
              <Rect x="190" y="200" width="190" height="80" fill={theme.colors.surfaceVariant} stroke={theme.colors.glass.border} strokeWidth="2" />

              {/* Animated Route Path */}
              <Path 
                d="M 70 100 L 70 150 L 320 150 L 320 200" 
                fill="none" 
                stroke={theme.colors.primary} 
                strokeWidth="4" 
                strokeDasharray="5,5" 
              />
              
              {/* Department Pins */}
              <Circle cx="70" cy="60" r="12" fill={theme.colors.accent} />
              <Circle cx="320" cy="80" r="12" fill={theme.colors.error} />
              
              {/* Current Location Marker */}
              <Circle cx="70" cy="100" r="8" fill={theme.colors.primary} />
              <Circle cx="70" cy="100" r="16" fill={theme.colors.primary} opacity="0.3" />
            </Svg>

            <View style={styles.floorSelector}>
              {['4', '3', '2', '1', 'G'].map(f => <FloorBtn key={f} floor={f} />)}
            </View>
          </Animated.View>
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          <NavioraText type="label" color="low" style={styles.sectionTitle}>DEPARTMENTS & DESTINATIONS</NavioraText>
          {loading ? (
            <ActivityIndicator color={theme.colors.primary} size="large" style={{ marginVertical: 20 }} />
          ) : filteredDepartments.length > 0 ? (
            <GlassCard style={{ padding: 8 }}>
              {filteredDepartments.map((dept, index) => (
                <React.Fragment key={dept.id || index}>
                  {index > 0 && <View style={styles.divider} />}
                  <DestinationItem
                    name={dept.name || dept.department_name}
                    icon={dept.icon || "medical"}
                    floor={dept.floor || 1}
                    color={theme.colors.primary}
                  />
                </React.Fragment>
              ))}
            </GlassCard>
          ) : (
            <GlassCard style={{ padding: 16 }}>
              <NavioraText type="body" color="low" style={{ textAlign: 'center' }}>
                No departments found.
              </NavioraText>
            </GlassCard>
          )}

          <GradientButton title="Start Navigation" style={{ marginTop: 32 }} />
          <View style={{ height: 100 }} />
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', padding: 24 },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  iconBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  searchContainer: { paddingHorizontal: 24, marginBottom: 20 },
  searchBar: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, height: 50 },
  searchInput: { flex: 1, marginLeft: 12, fontSize: 16 },
  mapArea: { height: 320, paddingHorizontal: 24, marginBottom: 32 },
  mapMock: { flex: 1, borderRadius: 24, borderWidth: 1, overflow: 'hidden', position: 'relative' },
  floorSelector: { position: 'absolute', right: 16, top: 16, gap: 8 },
  floorBtn: { width: 40, height: 40, borderRadius: 12, borderWidth: 1, justifyContent: 'center', alignItems: 'center' },
  room: { position: 'absolute', borderRadius: 8, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)' },
  path: { position: 'absolute', opacity: 0.6 },
  userDot: { position: 'absolute', width: 14, height: 14, borderRadius: 7, zIndex: 10 },
  userPulse: { position: 'absolute', width: 30, height: 30, borderRadius: 15, top: -8, left: -8, opacity: 0.3 },
  scrollContent: { paddingHorizontal: 24 },
  sectionTitle: { letterSpacing: 1.5, marginBottom: 16, fontWeight: '800' },
  destItem: { flexDirection: 'row', alignItems: 'center', padding: 16 },
  destIcon: { width: 48, height: 48, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  divider: { height: 1, backgroundColor: 'rgba(255,255,255,0.05)', marginHorizontal: 16 },
});
