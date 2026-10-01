import React, { useState, useEffect } from 'react';
import { StyleSheet, View, TouchableOpacity, SafeAreaView, ScrollView, Switch, Alert, Modal, Text } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { useTheme } from '../context/ThemeContext';
import { NavioraText, GlassCard, GradientButton } from '../components/common/AtomicComponents';
import { useLanguage, Language } from '../context/LanguageContext';

export default function SettingsScreen({ navigation }: any) {
  const theme = useTheme();
  const { language, setLanguage } = useLanguage();
  const [voiceGuidance, setVoiceGuidance] = useState(true);
  const [largeText, setLargeText] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  const languageNames: Record<Language, string> = { en: 'English', hi: 'हिन्दी', ta: 'தமிழ்', te: 'తెలుగు', es: 'Español' };
  const [langModalVisible, setLangModalVisible] = useState(false);
  
  useEffect(() => {
    const loadSettings = async () => {
      const v = await AsyncStorage.getItem('settings_voice');
      if (v !== null) setVoiceGuidance(v === 'true');
      const lt = await AsyncStorage.getItem('settings_largetext');
      if (lt !== null) setLargeText(lt === 'true');
      const dm = await AsyncStorage.getItem('settings_darkmode');
      if (dm !== null) setDarkMode(dm === 'true');
    };
    loadSettings();
  }, []);

  const saveSetting = async (key: string, value: string | boolean) => {
    await AsyncStorage.setItem(key, String(value));
  };

  const handleLogout = () => {
    Alert.alert(
      "Confirm Logout",
      "Are you sure you want to log out of your account?",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Logout", 
          style: "destructive",
          onPress: async () => {
            await AsyncStorage.removeItem('access_token');
            // Navigate to Auth or Login
            navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
          }
        }
      ]
    );
  };

  const SettingRow = ({ label, icon, type = 'chevron', color, isLast = false, value, onValueChange, onPress, subtext }: any) => (
    <TouchableOpacity style={[styles.row, !isLast && styles.divider]} onPress={onPress} disabled={!onPress && type !== 'switch'}>
      <View style={styles.labelGroup}>
        <View style={[styles.iconBox, { backgroundColor: (color || theme.colors.primary) + '20' }]}>
          <Ionicons name={icon} size={20} color={color || theme.colors.primary} />
        </View>
        <View style={{ marginLeft: 16 }}>
          <NavioraText type="label" style={{ fontSize: largeText ? 18 : 16 }}>{label}</NavioraText>
          {subtext && <NavioraText type="xs" color="low">{subtext}</NavioraText>}
        </View>
      </View>
      {type === 'chevron' ? (
        <Ionicons name="chevron-forward" size={20} color={theme.colors.text.low} />
      ) : (
        <Switch 
          value={value} 
          onValueChange={(val) => {
            onValueChange && onValueChange(val);
          }} 
          trackColor={{ true: theme.colors.primary }} 
        />
      )}
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
          <NavioraText type="h2" style={{ marginLeft: 12 }}>Settings</NavioraText>
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          <NavioraText type="label" color="low" style={styles.sectionTitle}>PREFERENCES</NavioraText>
          <GlassCard style={{ padding: 8, marginBottom: 32 }}>
            <SettingRow 
              label="Voice Guidance" 
              icon="mic" 
              type="switch" 
              value={voiceGuidance}
              onValueChange={(val: boolean) => { setVoiceGuidance(val); saveSetting('settings_voice', val); }}
            />
            <SettingRow 
              label="Language" 
              icon="language" 
              color={theme.colors.accent} 
              subtext={language}
              onPress={() => setLangModalVisible(true)}
            />
            <SettingRow 
              label="Dark Theme" 
              icon="moon" 
              type="switch" 
              color={theme.colors.purple}
              value={darkMode}
              onValueChange={(val: boolean) => { setDarkMode(val); saveSetting('settings_darkmode', val); }}
            />
            <SettingRow 
              label="Large Text" 
              icon="text" 
              type="switch" 
              color={theme.colors.warning} 
              isLast 
              value={largeText}
              onValueChange={(val: boolean) => { setLargeText(val); saveSetting('settings_largetext', val); }}
            />
          </GlassCard>

          <NavioraText type="label" color="low" style={styles.sectionTitle}>ACCOUNT & SECURITY</NavioraText>
          <GlassCard style={{ padding: 8, marginBottom: 32 }}>
            <SettingRow label="Account Details" icon="person" color={theme.colors.primary} />
            <SettingRow label="Biometric Access" icon="finger-print" type="switch" value={true} />
            <SettingRow label="Download Records" icon="cloud-download" color={theme.colors.primary} isLast />
          </GlassCard>

          <NavioraText type="label" color="low" style={styles.sectionTitle}>SYSTEM</NavioraText>
          <GlassCard style={{ padding: 8 }}>
            <SettingRow label="Privacy Policy" icon="shield-checkmark" />
            <SettingRow label="Terms of Service" icon="document-text" />
            <SettingRow label="Logout" icon="log-out" color={theme.colors.error} onPress={handleLogout} isLast />
          </GlassCard>

          <View style={{ height: 100 }} />
        </ScrollView>
      </SafeAreaView>

      {/* Language Selection Modal */}
      <Modal visible={langModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={[styles.modalSheet, { backgroundColor: '#161B2C' }]}>
            <NavioraText type="h2" style={{ marginBottom: 20 }}>Select Language</NavioraText>
            {(Object.keys(languageNames) as Language[]).map((lang) => (
              <TouchableOpacity 
                key={lang} 
                style={styles.langRow} 
                onPress={() => {
                  setLanguage(lang as Language);
                  saveSetting('settings_language', lang);
                  setLangModalVisible(false);
                }}
              >
                <NavioraText type="body">{languageNames[lang]}</NavioraText>
                {language === lang && <Ionicons name="checkmark" size={24} color={theme.colors.primary} />}
              </TouchableOpacity>
            ))}
            <TouchableOpacity onPress={() => setLangModalVisible(false)} style={{ marginTop: 20, alignItems: 'center' }}>
              <NavioraText type="body" color="low">Cancel</NavioraText>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', padding: 24 },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  scrollContent: { paddingHorizontal: 24 },
  sectionTitle: { letterSpacing: 1.5, marginBottom: 16, fontWeight: '800' },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16 },
  labelGroup: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  iconBox: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  divider: { borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.05)' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalSheet: { borderTopLeftRadius: 32, borderTopRightRadius: 32, padding: 24, paddingBottom: 40 },
  langRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' }
});
