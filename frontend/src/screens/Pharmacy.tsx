import React, { useEffect, useState } from 'react';
import { StyleSheet, View, ScrollView, TouchableOpacity, SafeAreaView, TextInput, ActivityIndicator, Dimensions } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInUp } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { NavioraText, GlassCard, StatusBadge, GradientButton } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';

const { width } = Dimensions.get('window');

export default function PharmacyScreen({ navigation }: any) {
  const theme = useTheme();

  const [prescriptions, setPrescriptions] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiService.get<any[]>('/pharmacy/prescriptions').then(result => {
      if (result.data) setPrescriptions(Array.isArray(result.data) ? result.data : []);
    });
    fetchInventory('');
  }, []);

  const fetchInventory = async (query: string) => {
    setLoading(true);
    const endpoint = query ? `/pharmacy/inventory?query=${encodeURIComponent(query)}` : '/pharmacy/inventory';
    const res = await apiService.get<any>(endpoint);
    setLoading(false);
    if (res.data) setInventory(res.data.medications || res.data || []);
  };

  const handleSearch = (text: string) => {
    setSearchQuery(text);
    fetchInventory(text);
  };

  const PrescriptionCard = ({ item, index }: any) => (
    <Animated.View entering={FadeInUp.delay(index * 100)}>
      <GlassCard style={styles.card}>
        <View style={styles.cardTop}>
          <View style={[styles.medIcon, { backgroundColor: theme.colors.primary + '20' }]}>
            <Ionicons name="medkit" size={24} color={theme.colors.primary} />
          </View>
          <View style={{ flex: 1, marginLeft: 16 }}>
            <NavioraText type="h3">{item.medication}</NavioraText>
            <NavioraText type="xs" color="low">{item.dosage || '500mg'} • Take after food</NavioraText>
          </View>
          <StatusBadge text={item.status || 'Active'} color="success" />
        </View>
        <View style={styles.cardDivider} />
        <View style={styles.cardBottom}>
          <View>
            <NavioraText type="xs" color="low">PRESCRIBED BY</NavioraText>
            <NavioraText type="label">{item.doctor || 'Dr. Sarah Johnson'}</NavioraText>
          </View>
          <TouchableOpacity style={styles.refillBtn}>
            <NavioraText type="label" color="primary">REFILL</NavioraText>
          </TouchableOpacity>
        </View>
      </GlassCard>
    </Animated.View>
  );

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={28} color="#FFF" />
          </TouchableOpacity>
          <NavioraText type="h2" style={{ flex: 1, marginLeft: 12 }}>Pharmacy</NavioraText>
          <TouchableOpacity style={styles.iconBtn}>
            <Ionicons name="cart-outline" size={24} color="#FFF" />
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          <View style={[styles.searchContainer, { backgroundColor: theme.colors.glass.bg, borderColor: theme.colors.glass.border }]}>
            <Ionicons name="search" size={20} color={theme.colors.text.low} />
            <TextInput
              placeholder="Search medications..."
              placeholderTextColor={theme.colors.text.low}
              value={searchQuery}
              onChangeText={handleSearch}
              style={[styles.searchInput, { color: theme.colors.text.high }]}
            />
          </View>

          <NavioraText type="label" color="low" style={styles.sectionTitle}>ACTIVE PRESCRIPTIONS</NavioraText>
          {prescriptions.length > 0 ? (
            prescriptions.map((apt, idx) => <PrescriptionCard key={apt.id} item={apt} index={idx} />)
          ) : (
            <GlassCard style={styles.emptyCard}><NavioraText color="low">No active prescriptions.</NavioraText></GlassCard>
          )}

          <NavioraText type="label" color="low" style={[styles.sectionTitle, { marginTop: 32 }]}>INVENTORY STATUS</NavioraText>
          {loading ? (
            <ActivityIndicator size="small" color={theme.colors.primary} />
          ) : (
            inventory.map((item, idx) => (
              <GlassCard key={idx} style={[styles.inventoryCard, item.low_stock_alert && { borderLeftWidth: 4, borderLeftColor: theme.colors.error }]}>
                <View style={{ flex: 1 }}>
                  <NavioraText type="h3">{item.medication_name || item.name}</NavioraText>
                  <NavioraText type="xs" color="low">{item.category} • {item.location}</NavioraText>
                </View>
                <View style={styles.stockBadge}>
                  <NavioraText type="label" color={item.low_stock_alert ? 'error' : 'primary'}>
                    {item.quantity || 0} PCS
                  </NavioraText>
                </View>
              </GlassCard>
            ))
          )}

          <GlassCard style={styles.infoCard}>
            <View style={styles.infoHeader}>
              <Ionicons name="location" size={24} color={theme.colors.accent} />
              <NavioraText type="h3" style={{ marginLeft: 12 }}>Main Pharmacy</NavioraText>
            </View>
            <NavioraText type="body" color="low" style={{ marginTop: 8 }}>
              Ground Floor, Block A. Open 24/7 for emergency and inpatient needs.
            </NavioraText>
            <View style={styles.infoFooter}>
              <StatusBadge text="Open Now" color="success" />
              <TouchableOpacity><NavioraText type="label" color="primary">Call Support</NavioraText></TouchableOpacity>
            </View>
          </GlassCard>

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
  scrollContent: { paddingHorizontal: 24 },
  searchContainer: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, height: 56, borderRadius: 16, borderWidth: 1, marginBottom: 32 },
  searchInput: { flex: 1, marginLeft: 12, fontSize: 16, fontWeight: '500' },
  sectionTitle: { letterSpacing: 1.5, marginBottom: 16, fontWeight: '800' },
  card: { padding: 20, marginBottom: 16 },
  cardTop: { flexDirection: 'row', alignItems: 'center' },
  medIcon: { width: 48, height: 48, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  cardDivider: { height: 1, backgroundColor: 'rgba(255,255,255,0.05)', marginVertical: 16 },
  cardBottom: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  refillBtn: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 12, backgroundColor: 'rgba(14, 165, 233, 0.1)' },
  emptyCard: { padding: 20, alignItems: 'center' },
  inventoryCard: { flexDirection: 'row', alignItems: 'center', padding: 16, marginBottom: 12 },
  stockBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.05)' },
  infoCard: { padding: 20, marginTop: 32 },
  infoHeader: { flexDirection: 'row', alignItems: 'center' },
  infoFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 20 },
});
