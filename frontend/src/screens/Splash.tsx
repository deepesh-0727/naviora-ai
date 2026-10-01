import React, { useEffect } from 'react';
import { StyleSheet, View, Animated, Dimensions } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { useTheme } from '../context/ThemeContext';
import { NavioraText, PulseAnimation } from '../components/common/AtomicComponents';

const { height, width } = Dimensions.get('window');

export default function SplashScreen({ navigation }: any) {
  const theme = useTheme();
  const fadeAnim = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 1000,
      useNativeDriver: true,
    }).start();

    const checkAuth = async () => {
      const token = await AsyncStorage.getItem('access_token');
      setTimeout(() => {
        navigation.replace(token ? 'Main' : 'Login');
      }, 2500);
    };

    checkAuth();
  }, [navigation]);

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />

      <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
        <PulseAnimation color={theme.colors.primary} size={160}>
          <View style={[styles.logoWrapper, { backgroundColor: 'rgba(255,255,255,0.05)', borderColor: theme.colors.glass.border }]}>
            <Ionicons name="pulse" size={72} color="#FFFFFF" />
          </View>
        </PulseAnimation>

        <NavioraText type="h1" style={styles.title}>Naviora AI</NavioraText>
        <NavioraText type="body" color="low" style={styles.subtitle}>Your Health, Our Priority</NavioraText>
      </Animated.View>

      <View style={styles.footer}>
        <View style={styles.badgeRow}>
          <View style={styles.badge}>
            <Ionicons name="shield-checkmark" size={16} color={theme.colors.accent} />
            <NavioraText type="xs" style={{ marginLeft: 6, color: theme.colors.text.low }}>HIPAA COMPLIANT</NavioraText>
          </View>
          <View style={styles.vDivider} />
          <View style={styles.badge}>
            <Ionicons name="business" size={16} color={theme.colors.accent} />
            <NavioraText type="xs" style={{ marginLeft: 6, color: theme.colors.text.low }}>24/7 SUPPORT</NavioraText>
          </View>
        </View>
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  content: { alignItems: 'center' },
  logoWrapper: {
    width: 120,
    height: 120,
    borderRadius: 40,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 10,
  },
  title: { fontSize: 42, marginTop: 40, fontFamily: 'Inter_800ExtraBold', color: '#FFF' },
  subtitle: { marginTop: 8, letterSpacing: 2, fontWeight: '500' },
  footer: { position: 'absolute', bottom: 60, width: '100%', alignItems: 'center' },
  badgeRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.03)', paddingHorizontal: 20, paddingVertical: 12, borderRadius: 20, borderWidth: 1, borderColor: 'rgba(255,255,255,0.05)' },
  badge: { flexDirection: 'row', alignItems: 'center' },
  vDivider: { width: 1, height: 16, backgroundColor: 'rgba(255,255,255,0.1)', marginHorizontal: 16 },
});
