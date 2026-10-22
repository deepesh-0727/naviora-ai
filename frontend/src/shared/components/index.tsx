import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, TouchableOpacity, View, type ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, RADIUS } from '../theme';

export const Button = ({
  title,
  onPress,
  disabled,
  loading = false,
  variant = 'primary',
  style,
}: {
  title: string;
  onPress?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary' | 'danger';
  style?: ViewStyle;
}) => (
  <TouchableOpacity
    disabled={disabled || loading}
    accessibilityRole="button"
    onPress={onPress}
    style={[
      styles.button,
      variant === 'secondary' && styles.secondary,
      variant === 'danger' && styles.danger,
      disabled && styles.disabled,
      style,
    ]}
  >
    <View style={styles.buttonContent}>
      {loading ? <ActivityIndicator size="small" color={variant === 'secondary' ? COLORS.primary : COLORS.white} style={styles.buttonSpinner} /> : null}
      <Text style={[styles.buttonText, variant === 'secondary' && styles.buttonTextSecondary]}>{title}</Text>
    </View>
  </TouchableOpacity>
);

export const Card = ({ children, style }: { children: React.ReactNode; style?: ViewStyle | (ViewStyle | false | undefined)[] }) => (
  <View style={[styles.card, style as ViewStyle]}>{children}</View>
);

export const Input = ({
  label,
  value,
  onChangeText,
  placeholder,
  secureTextEntry,
}: {
  label?: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  secureTextEntry?: boolean;
}) => (
  <View style={styles.inputWrap}>
    {label ? <Text style={styles.label}>{label}</Text> : null}
    <TextInput
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      secureTextEntry={secureTextEntry}
      style={styles.input}
    />
  </View>
);

export const Loader = ({ message = 'Loading...' }: { message?: string }) => (
  <View style={styles.centered}>
    <ActivityIndicator size="small" />
    <Text style={styles.muted}>{message}</Text>
  </View>
);

export const EmptyState = ({ message = 'No data available.' }: { message?: string }) => (
  <View style={styles.centered}>
    <Ionicons name="folder-open-outline" size={30} color={COLORS.textMuted} style={{ marginBottom: 8 }} />
    <Text style={styles.muted}>{message}</Text>
  </View>
);

export const ErrorState = ({ message = 'There was an error.', onRetry }: { message?: string; onRetry?: () => void }) => (
  <View style={styles.centered}>
    <Text style={styles.error}>{message}</Text>
    {onRetry ? <Button title="Retry" variant="secondary" onPress={onRetry} style={{ marginTop: 12 }} /> : null}
  </View>
);

export const Toast = ({ message }: { message: string }) => (
  <View style={styles.toast}>
    <Text style={styles.toastText}>{message}</Text>
  </View>
);

export const Badge = ({ label, color = COLORS.primaryLight }: { label: string; color?: string }) => (
  <View style={[styles.badge, { backgroundColor: color }]}>
    <Text style={[styles.badgeText, color !== COLORS.primaryLight && styles.badgeTextOnColor]}>{label}</Text>
  </View>
);

export const Tabs = ({ items, activeIndex, onChange }: { items: string[]; activeIndex: number; onChange: (index: number) => void }) => (
  <View style={styles.tabs}>
    {items.map((item, index) => (
      <Pressable key={item} onPress={() => onChange(index)} style={[styles.tab, index === activeIndex && styles.tabActive]}>
        <Text style={[styles.tabText, index === activeIndex && styles.tabTextActive]}>{item}</Text>
      </Pressable>
    ))}
  </View>
);

export const Modal = ({ visible, children }: { visible: boolean; children: React.ReactNode }) => {
  if (!visible) return null;
  return <View style={styles.modal}>{children}</View>;
};

export const ConfirmDialog = ({ title, message, onConfirm, onCancel }: { title: string; message: string; onConfirm: () => void; onCancel: () => void }) => (
  <View style={styles.dialog}>
    <Text style={styles.dialogTitle}>{title}</Text>
    <Text style={styles.muted}>{message}</Text>
    <View style={styles.dialogActions}>
      <Button title="Cancel" variant="secondary" onPress={onCancel} />
      <Button title="Confirm" variant="primary" onPress={onConfirm} />
    </View>
  </View>
);

export const Avatar = ({ label, size = 40 }: { label: string; size?: number }) => (
  <View style={[styles.avatar, { width: size, height: size, borderRadius: size / 2 }]}>
    <Text style={styles.avatarText}>{label.slice(0, 2).toUpperCase()}</Text>
  </View>
);

export const ScreenContainer = ({ children, style }: { children: React.ReactNode; style?: ViewStyle }) => (
  <SafeAreaView edges={['top', 'left', 'right']} style={[styles.screenContainer, style]}>{children}</SafeAreaView>
);

export const SectionHeader = ({ title }: { title: string }) => <Text style={styles.header}>{title}</Text>;

export const Header = ({ title, subtitle, onBack, right }: { title: string; subtitle?: string; onBack?: () => void; right?: React.ReactNode }) => (
  <View style={styles.headerRow}>
    {onBack ? <TouchableOpacity onPress={onBack} accessibilityRole="button" accessibilityLabel="Go back" style={styles.backButton}><Ionicons name="arrow-back" size={20} color={COLORS.text} /></TouchableOpacity> : null}
    <View style={styles.headerCopy}><Text style={styles.header}>{title}</Text>{subtitle ? <Text style={styles.headerSubtitle}>{subtitle}</Text> : null}</View>
    {right}
  </View>
);

export const BackendNotAvailable = ({ endpoint }: { endpoint: string }) => (
  <View style={styles.centered}>
    <Text style={styles.unavailableIcon}>🔌</Text>
    <Text style={styles.unavailableTitle}>Endpoint Not Available</Text>
    <Text style={styles.unavailableEndpoint}>{endpoint}</Text>
    <Text style={styles.muted}>The backend endpoint has not been implemented yet.</Text>
  </View>
);

export const InfoRow = ({ label, value }: { label: string; value?: string | null }) => (
  <View style={styles.infoRow}>
    <Text style={styles.infoLabel}>{label}</Text>
    <Text style={styles.infoValue}>{value ?? '—'}</Text>
  </View>
);

const styles = StyleSheet.create({
  button: { backgroundColor: COLORS.primary, borderRadius: RADIUS.full, paddingVertical: 13, paddingHorizontal: 18, alignItems: 'center' },
  buttonContent: { flexDirection: 'row', alignItems: 'center' },
  buttonSpinner: { marginRight: 8 },
  secondary: { backgroundColor: COLORS.white, borderWidth: 1, borderColor: COLORS.primary },
  danger: { backgroundColor: COLORS.danger },
  disabled: { opacity: 0.5 },
  buttonText: { color: COLORS.white, fontWeight: '600' },
  buttonTextSecondary: { color: COLORS.primary },
  card: { backgroundColor: COLORS.surface, borderRadius: RADIUS.lg, padding: 16, borderWidth: 1, borderColor: COLORS.border, shadowColor: COLORS.text, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.05, shadowRadius: 10, elevation: 2 },
  inputWrap: { marginBottom: 12 },
  label: { fontSize: 12, color: COLORS.textMuted, marginBottom: 6 },
  input: { borderWidth: 1, borderColor: COLORS.border, borderRadius: RADIUS.md, padding: 12, backgroundColor: COLORS.background, color: COLORS.text },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 16 },
  muted: { color: COLORS.textMuted, marginTop: 8 },
  error: { color: COLORS.danger, marginTop: 8 },
  toast: { backgroundColor: COLORS.text, paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10, position: 'absolute', bottom: 32, left: 16, right: 16 },
  toastText: { color: COLORS.white, textAlign: 'center' },
  badge: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, alignSelf: 'flex-start' },
  badgeText: { color: COLORS.primary, fontSize: 10, fontWeight: '700' },
  badgeTextOnColor: { color: COLORS.white },
  tabs: { flexDirection: 'row', gap: 8 },
  tab: { paddingVertical: 8, paddingHorizontal: 12, borderRadius: 999, backgroundColor: COLORS.background, borderWidth: 1, borderColor: COLORS.border },
  tabActive: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  tabText: { color: COLORS.textMuted },
  tabTextActive: { color: COLORS.white, fontWeight: '600' },
  modal: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.33)', justifyContent: 'center', padding: 24 },
  dialog: { backgroundColor: COLORS.white, borderRadius: RADIUS.lg, padding: 20 },
  dialogTitle: { fontSize: 18, fontWeight: '700', marginBottom: 8 },
  dialogActions: { marginTop: 16, flexDirection: 'row', gap: 12, justifyContent: 'flex-end' },
  avatar: { backgroundColor: COLORS.primaryLight, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: COLORS.primary },
  avatarText: { color: COLORS.primary, fontWeight: '700' },
  screenContainer: { flex: 1, backgroundColor: COLORS.background, padding: 16 },
  header: { fontSize: 22, fontWeight: '800', color: COLORS.text, marginBottom: 5 },
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 14 },
  headerCopy: { flex: 1 },
  headerSubtitle: { color: COLORS.textMuted, fontSize: 14, lineHeight: 20 },
  backButton: { width: 42, height: 42, marginRight: 12, borderRadius: 21, backgroundColor: COLORS.white, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: COLORS.border },
  unavailableIcon: { fontSize: 36, marginBottom: 8 },
  unavailableTitle: { fontSize: 16, fontWeight: '700', color: COLORS.text, marginBottom: 4 },
  unavailableEndpoint: { fontSize: 12, color: COLORS.textMuted, fontFamily: 'monospace', marginBottom: 4 },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderColor: COLORS.border },
  infoLabel: { fontSize: 14, color: COLORS.textMuted, flex: 1 },
  infoValue: { fontSize: 14, fontWeight: '600', color: COLORS.text, flex: 2, textAlign: 'right' },
});

export default {
  Button,
  Card,
  Input,
  Loader,
  EmptyState,
  ErrorState,
  Toast,
  Badge,
  Tabs,
  Modal,
  ConfirmDialog,
  Avatar,
  ScreenContainer,
  SectionHeader,
  BackendNotAvailable,
  InfoRow,
  Header,
};
