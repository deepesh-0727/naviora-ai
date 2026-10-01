import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated as RNAnimated,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../context/ThemeContext';

export const NavioraText = ({ children, type = 'body', color = 'primary', style, align = 'left' }: any) => {
  const theme = useTheme();
  const config = (theme.typography as any)[type] || theme.typography.body;
  const textPalette = theme.colors.text || {};
  const resolvedColor =
    color === 'primary'
      ? textPalette.primary || theme.colors.textPrimary || '#1A1A1A'
      : color === 'secondary'
        ? textPalette.secondary || theme.colors.textSecondary || '#6B7280'
        : color === 'inverse'
          ? textPalette.inverse || theme.colors.textInverse || '#FFFFFF'
          : color === 'muted'
            ? textPalette.muted || theme.colors.textMuted || '#9CA3AF'
            : color === 'low'
              ? textPalette.low || theme.colors.textLow || '#6B7280'
              : color === 'high'
                ? textPalette.high || theme.colors.textHigh || '#1A1A1A'
                : (textPalette as any)[color] || (theme.colors as any)[color] || textPalette.primary || '#1A1A1A';

  return (
    <Text style={[{ fontSize: config.size, fontWeight: config.weight, color: resolvedColor, textAlign: align }, style]}>
      {children}
    </Text>
  );
};

export const GlassCard = ({ children, style }: any) => {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
          borderRadius: theme.borderRadius.md,
          shadowColor: theme.colors.shadow,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
};

export const GradientButton = ({
  title,
  onPress,
  variant = 'primary',
  loading = false,
  disabled = false,
  style,
  icon,
}: any) => {
  const theme = useTheme();
  const scale = useRef(new RNAnimated.Value(1)).current;

  useEffect(() => {
    const pulse = RNAnimated.timing(scale, { toValue: 1.02, duration: 120, useNativeDriver: true });
    scale.setValue(1);
    pulse.start();
    return () => pulse.stop();
  }, [scale]);

  const colors = (theme.colors.gradients as any)[variant] || theme.colors.gradients.primary;
  const textColor = variant === 'secondary' ? theme.colors.primary : '#fff';

  return (
    <TouchableOpacity
      activeOpacity={0.9}
      disabled={disabled || loading}
      onPress={onPress}
      style={[styles.btnBase, { opacity: disabled ? 0.6 : 1 }, style]}
    >
      <LinearGradient
        colors={variant === 'secondary' ? [theme.colors.surface, theme.colors.primaryLight] : colors}
        style={[styles.btnGradient, { borderRadius: theme.borderRadius.sm, borderWidth: variant === 'secondary' ? 1 : 0, borderColor: theme.colors.primary }]}
      >
        {loading ? (
          <ActivityIndicator color={textColor} size="small" />
        ) : (
          <View style={styles.buttonContent}>
            {icon && <Ionicons name={icon} size={18} color={textColor} style={{ marginRight: 8 }} />}
            <NavioraText type="body" color={variant === 'secondary' ? 'primary' : 'inverse'} style={styles.buttonText}>{title}</NavioraText>
          </View>
        )}
      </LinearGradient>
    </TouchableOpacity>
  );
};

export const FloatingLabelInput = ({ label, value, onChangeText, icon, secureTextEntry, ...props }: any) => {
  const theme = useTheme();
  const [focused, setFocused] = useState(false);

  return (
    <View style={styles.inputContainer}>
      {label ? <NavioraText type="label" color="secondary" style={{ marginBottom: 8 }}>{label}</NavioraText> : null}
      <View
        style={[
          styles.inputWrapper,
          {
            borderColor: focused ? theme.colors.primary : theme.colors.border,
            backgroundColor: theme.colors.surface,
            borderRadius: theme.borderRadius.sm,
          },
        ]}
      >
        {icon && <Ionicons name={icon} size={18} color={focused ? theme.colors.primary : theme.colors.text.secondary} style={styles.inputIcon} />}
        <TextInput
          value={value}
          onChangeText={onChangeText}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholderTextColor={theme.colors.text.secondary}
          secureTextEntry={secureTextEntry}
          style={[styles.textInput, { color: theme.colors.text.primary }]}
          {...props}
        />
      </View>
    </View>
  );
};

export const StatusBadge = ({ text, color = 'success', icon }: any) => {
  const theme = useTheme();
  const palette: any = {
    primary: { bg: theme.colors.primaryLight, text: theme.colors.primary },
    success: { bg: '#DCFCE7', text: '#15803D' },
    danger: { bg: theme.colors.redSoft, text: theme.colors.danger },
    warning: { bg: theme.colors.amberSoft, text: theme.colors.warning },
    info: { bg: theme.colors.blueSoft, text: theme.colors.info },
    accent: { bg: theme.colors.primaryLight, text: theme.colors.primary },
  };
  const active = palette[color] || palette.primary;

  return (
    <View style={[styles.badge, { backgroundColor: active.bg, borderRadius: 999 }]}>
      {icon && <Ionicons name={icon} size={12} color={active.text} style={{ marginRight: 4 }} />}
      <NavioraText type="label" style={{ color: active.text }}>{String(text).toUpperCase()}</NavioraText>
    </View>
  );
};

export const PulseAnimation = ({ children, color, size = 100 }: any) => {
  const theme = useTheme();
  const pulse = useRef(new RNAnimated.Value(0)).current;

  useEffect(() => {
    const animation = RNAnimated.loop(
      RNAnimated.sequence([
        RNAnimated.timing(pulse, { toValue: 1, duration: 1200, useNativeDriver: true }),
        RNAnimated.timing(pulse, { toValue: 0, duration: 1200, useNativeDriver: true }),
      ])
    );
    animation.start();
    return () => animation.stop();
  }, [pulse]);

  const animatedStyle = {
    transform: [{ scale: pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.25] }) }],
    opacity: pulse.interpolate({ inputRange: [0, 1], outputRange: [0.7, 0] }),
  };

  return (
    <View style={styles.pulseContainer}>
      <RNAnimated.View
        style={[
          styles.pulseRing,
          animatedStyle,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            backgroundColor: color || theme.colors.primary,
          },
        ]}
      />
      {children}
    </View>
  );
};

export const Shimmer = ({ width, height, style }: any) => {
  const theme = useTheme();
  return <View style={[styles.shimmer, { width: width || '100%', height: height || 20, backgroundColor: theme.colors.primaryLight }, style]} />;
};

export const NavioraButton = GradientButton;
export const NavioraCard = GlassCard;
export const NavioraHeader = ({ title, subtitle, onBack, rightAction, showBack = true }: any) => {
  const theme = useTheme();
  return (
    <View style={[styles.headerWrap, { backgroundColor: theme.colors.background }]}> 
      <View style={styles.headerRow}>
        {showBack ? (
          <TouchableOpacity onPress={onBack} style={styles.iconButton} activeOpacity={0.8}>
            <Ionicons name="arrow-back" size={22} color={theme.colors.text.primary} />
          </TouchableOpacity>
        ) : (
          <View style={styles.iconButtonPlaceholder} />
        )}

        <View style={styles.headerTextWrap}>
          <NavioraText type="h2" style={{ color: theme.colors.text.primary }}>{title}</NavioraText>
          {subtitle ? <NavioraText type="caption" color="secondary" style={{ marginTop: 2 }}>{subtitle}</NavioraText> : null}
        </View>

        {rightAction ? <View style={styles.rightAction}>{rightAction}</View> : <View style={styles.iconButtonPlaceholder} />}
      </View>
    </View>
  );
};

export const NavioraChip = ({ label, active = false, onPress, style }: any) => {
  const theme = useTheme();
  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.85} style={[styles.chip, { backgroundColor: active ? theme.colors.primary : theme.colors.primaryLight, borderRadius: theme.borderRadius.full }, style]}>
      <NavioraText type="caption" color={active ? 'inverse' : 'primary'}>{label}</NavioraText>
    </TouchableOpacity>
  );
};

export const NavioraInput = FloatingLabelInput;

export const NavioraToggle = ({ value, onValueChange }: any) => {
  const theme = useTheme();
  return (
    <TouchableOpacity activeOpacity={0.85} onPress={() => onValueChange(!value)} style={[styles.toggle, { backgroundColor: value ? theme.colors.primary : '#E5E7EB', borderColor: value ? theme.colors.primary : '#E5E7EB' }]}>
      <View style={[styles.toggleThumb, { transform: [{ translateX: value ? 18 : 0 }], backgroundColor: '#fff' }]} />
    </TouchableOpacity>
  );
};

export const NavioraAvatar = ({ source, size = 48, showOnline = false, style }: any) => {
  const theme = useTheme();
  const dimension = typeof size === 'number' ? size : 48;
  return (
    <View style={[styles.avatarWrap, { width: dimension, height: dimension, borderRadius: dimension / 2 }, style]}>
      <View style={[styles.avatar, { width: dimension, height: dimension, borderRadius: dimension / 2, backgroundColor: '#D8E2DC' }]}>
        <Text style={{ fontSize: dimension * 0.35, fontWeight: '700', color: theme.colors.primary }}>{source || 'A'}</Text>
      </View>
      {showOnline ? <View style={[styles.onlineBadge, { backgroundColor: theme.colors.success }]} /> : null}
    </View>
  );
};

export const NavioraBadge = ({ label, tone = 'sage', style }: any) => {
  const theme = useTheme();
  const palette: any = {
    sage: { bg: theme.colors.primaryLight, text: theme.colors.primary, dot: theme.colors.primary },
    success: { bg: '#DCFCE7', text: '#15803D', dot: '#22C55E' },
    danger: { bg: theme.colors.redSoft, text: theme.colors.danger, dot: theme.colors.danger },
    info: { bg: theme.colors.blueSoft, text: theme.colors.info, dot: theme.colors.info },
    warning: { bg: theme.colors.amberSoft, text: theme.colors.warning, dot: theme.colors.warning },
  };
  const colors = palette[tone] || palette.sage;

  return (
    <View style={[styles.badgePill, { backgroundColor: colors.bg, borderRadius: 999 }, style]}>
      <View style={[styles.badgeDot, { backgroundColor: colors.dot }]} />
      <NavioraText type="label" style={{ color: colors.text }}>{label}</NavioraText>
    </View>
  );
};

export const NavioraTabSelector = ({ tabs, activeTab, onChange }: any) => {
  const theme = useTheme();
  return (
    <View style={styles.tabSelector}>
      {tabs.map((tab: string, index: number) => {
        const active = activeTab === index || activeTab === tab;
        return (
          <TouchableOpacity key={tab} activeOpacity={0.85} onPress={() => onChange(index)} style={[styles.tabButton, { backgroundColor: active ? theme.colors.primary : theme.colors.primaryLight, borderRadius: 999 }]}>
            <NavioraText type="caption" color={active ? 'inverse' : 'primary'}>{tab}</NavioraText>
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

export const NavioraBottomNav = ({ items, activeIndex, onChange }: any) => {
  const theme = useTheme();
  return (
    <View style={[styles.bottomNav, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}>
      {items.map((item: any, index: number) => (
        <TouchableOpacity key={item.label} activeOpacity={0.85} onPress={() => onChange(index)} style={styles.navItem}>
          <Ionicons name={activeIndex === index ? item.activeIcon : item.icon} size={22} color={activeIndex === index ? theme.colors.primary : '#7D8A89'} />
          <NavioraText type="label" color={activeIndex === index ? 'primary' : 'secondary'} style={{ marginTop: 4 }}>{item.label}</NavioraText>
        </TouchableOpacity>
      ))}
    </View>
  );
};

export const NavioraEmptyState = ({ icon = 'mail-outline', title, description, actionLabel, onPress }: any) => {
  const theme = useTheme();
  return (
    <View style={styles.emptyState}>
      <View style={[styles.emptyIcon, { backgroundColor: theme.colors.primaryLight }]}>
        <Ionicons name={icon} size={32} color={theme.colors.primary} />
      </View>
      <NavioraText type="h3" style={{ marginTop: 18 }}>{title}</NavioraText>
      <NavioraText type="caption" color="secondary" align="center" style={{ marginTop: 8, maxWidth: 280 }}>{description}</NavioraText>
      {actionLabel ? (
        <View style={{ marginTop: 18, width: '100%' }}>
          <NavioraButton label={actionLabel} onPress={onPress} />
        </View>
      ) : null}
    </View>
  );
};

export const NavioraSOSButton = ({ onPress, disabled = false }: any) => {
  const theme = useTheme();
  const scale = useRef(new RNAnimated.Value(1)).current;

  useEffect(() => {
    const animation = RNAnimated.loop(
      RNAnimated.sequence([
        RNAnimated.timing(scale, { toValue: 1.08, duration: 900, useNativeDriver: true }),
        RNAnimated.timing(scale, { toValue: 1, duration: 900, useNativeDriver: true }),
      ])
    );
    animation.start();
    return () => animation.stop();
  }, [scale]);

  return (
    <RNAnimated.View style={{ transform: [{ scale }] }}>
      <TouchableOpacity onPress={onPress} disabled={disabled} activeOpacity={0.9} style={[styles.sosButton, { backgroundColor: theme.colors.danger, borderColor: theme.colors.dangerDark }]}>
        <View style={styles.sosInner}>
          <Ionicons name="warning" size={28} color="#fff" />
        </View>
      </TouchableOpacity>
    </RNAnimated.View>
  );
};

export const NavioraWaveform = ({ active = true, bars = 8 }: any) => {
  const [values, setValues] = useState<number[]>([]);
  useEffect(() => {
    const next = Array.from({ length: bars }, (_, index) => Math.random() * 40 + 8 + (index % 3) * 8);
    setValues(next);
    const interval = setInterval(() => {
      setValues(Array.from({ length: bars }, (_, index) => Math.random() * 30 + 10 + (index % 2) * 12));
    }, 500);
    return () => clearInterval(interval);
  }, [bars]);

  return (
    <View style={styles.waveformRow}>
      {values.map((height, index) => (
        <View key={index} style={[styles.waveBar, { height: active ? height : 14, backgroundColor: index % 2 === 0 ? '#8FA998' : '#3A5A40', opacity: active ? 1 : 0.4 }]} />
      ))}
    </View>
  );
};

export const NavioraMicButton = ({ onPress, size = 120 }: any) => {
  const theme = useTheme();
  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.9} style={[styles.micButtonWrap, { width: size, height: size }]}>
      <View style={[styles.micPulse, { width: size + 20, height: size + 20, borderColor: '#D8E2DC' }]} />
      <View style={[styles.micButton, { width: size, height: size, backgroundColor: theme.colors.primary }]}>
        <Ionicons name="mic" size={size * 0.38} color="#fff" />
      </View>
    </TouchableOpacity>
  );
};

export const NavioraListItem = ({ icon, title, subtitle, rightIcon = 'chevron-forward', onPress, style }: any) => {
  const theme = useTheme();
  return (
    <TouchableOpacity activeOpacity={0.8} onPress={onPress} style={[styles.listItem, { borderColor: theme.colors.border }, style]}>
      <View style={[styles.listIcon, { backgroundColor: theme.colors.primaryLight }]}>
        <Ionicons name={icon} size={18} color={theme.colors.primary} />
      </View>
      <View style={styles.listTextWrap}>
        <NavioraText type="body">{title}</NavioraText>
        {subtitle ? <NavioraText type="caption" color="secondary">{subtitle}</NavioraText> : null}
      </View>
      <Ionicons name={rightIcon} size={18} color={theme.colors.text.secondary} />
    </TouchableOpacity>
  );
};

export const NavioraStatCard = ({ icon, value, label, meta, tone = 'sage' }: any) => {
  const theme = useTheme();
  const toneMap: any = {
    sage: { bg: '#D8E2DC', color: theme.colors.primary },
    amber: { bg: '#FDE68A', color: '#B45309' },
    red: { bg: '#FECACA', color: '#B91C1C' },
    blue: { bg: '#DBEAFE', color: '#1D4ED8' },
  };
  const palette = toneMap[tone] || toneMap.sage;

  return (
    <GlassCard style={styles.statCard}>
      <View style={[styles.statIcon, { backgroundColor: palette.bg }]}>
        <Ionicons name={icon} size={20} color={palette.color} />
      </View>
      <NavioraText type="h3" style={{ marginTop: 14 }}>{value}</NavioraText>
      <NavioraText type="label" color="secondary" style={{ marginTop: 4 }}>{label}</NavioraText>
      {meta ? <NavioraText type="caption" color="secondary" style={{ marginTop: 4 }}>{meta}</NavioraText> : null}
    </GlassCard>
  );
};

export const NavioraToast = ({ visible, message, onDismiss }: any) => {
  const theme = useTheme();
  if (!visible) return null;
  return (
    <View style={[styles.toast, { backgroundColor: theme.colors.primaryDark }]}>
      <NavioraText type="caption" color="inverse">{message}</NavioraText>
      <TouchableOpacity onPress={onDismiss} style={{ marginLeft: 12 }}>
        <Ionicons name="close" size={18} color="#fff" />
      </TouchableOpacity>
    </View>
  );
};

export const NavioraProgressBar = ({ progress = 0.5, total = 3, current = 1 }: any) => {
  const theme = useTheme();
  return (
    <View style={styles.progressWrap}>
      <View style={styles.progressMetaRow}>
        <NavioraText type="caption" color="secondary">Step {current} of {total}</NavioraText>
        <NavioraText type="caption" color="secondary">{Math.round(progress * 100)}%</NavioraText>
      </View>
      <View style={[styles.progressTrack, { backgroundColor: theme.colors.primaryLight }]}>
        <View style={[styles.progressFill, { width: `${Math.max(0, Math.min(100, progress * 100))}%`, backgroundColor: theme.colors.primary }]} />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
    elevation: 2,
    padding: 16,
  },
  btnBase: {
    width: '100%',
  },
  btnGradient: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    paddingHorizontal: 18,
  },
  buttonText: {
    fontWeight: '700',
  },
  buttonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  inputContainer: {
    width: '100%',
    marginBottom: 16,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    paddingHorizontal: 12,
    height: 52,
  },
  inputIcon: {
    marginRight: 10,
  },
  textInput: {
    flex: 1,
    fontSize: 15,
    fontWeight: '500',
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    alignSelf: 'flex-start',
  },
  pulseContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  pulseRing: {
    position: 'absolute',
  },
  shimmer: {
    borderRadius: 12,
    opacity: 0.8,
  },
  headerWrap: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 10,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTextWrap: {
    flex: 1,
    marginHorizontal: 8,
  },
  iconButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#F3F7F2',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconButtonPlaceholder: {
    width: 36,
    height: 36,
  },
  rightAction: {
    minWidth: 36,
    alignItems: 'flex-end',
  },
  chip: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginRight: 8,
  },
  tabSelector: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  tabButton: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  toggle: {
    width: 44,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    paddingHorizontal: 4,
    borderWidth: 1,
  },
  toggleThumb: {
    width: 18,
    height: 18,
    borderRadius: 9,
  },
  avatarWrap: {
    position: 'relative',
  },
  avatar: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  onlineBadge: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: '#fff',
  },
  badgePill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 5,
    alignSelf: 'flex-start',
  },
  badgeDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    marginRight: 6,
  },
  bottomNav: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 12,
    paddingBottom: 16,
    borderTopWidth: 1,
    backgroundColor: '#fff',
  },
  navItem: {
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 60,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 28,
  },
  emptyIcon: {
    width: 74,
    height: 74,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sosButton: {
    width: 180,
    height: 180,
    borderRadius: 90,
    borderWidth: 8,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#DC2626',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 20,
    elevation: 8,
  },
  sosInner: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#EF4444',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: '#fff',
  },
  waveformRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    height: 46,
    gap: 4,
  },
  waveBar: {
    width: 8,
    borderRadius: 8,
    minHeight: 10,
  },
  micButtonWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  micPulse: {
    position: 'absolute',
    borderWidth: 2,
    borderRadius: 999,
  },
  micButton: {
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#3A5A40',
    shadowOpacity: 0.22,
    shadowRadius: 18,
    elevation: 5,
  },
  listItem: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 16,
    padding: 12,
    marginBottom: 10,
  },
  listIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  listTextWrap: {
    flex: 1,
  },
  statCard: {
    minWidth: 110,
    marginRight: 12,
  },
  statIcon: {
    width: 38,
    height: 38,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  toast: {
    position: 'absolute',
    top: 60,
    left: 16,
    right: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 12,
    zIndex: 20,
  },
  progressWrap: {
    marginVertical: 12,
  },
  progressMetaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  progressTrack: {
    height: 8,
    borderRadius: 999,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 999,
  },
});
