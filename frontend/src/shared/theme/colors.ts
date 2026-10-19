export const COLORS = {
  primary: '#275A4A',
  primaryLight: '#E6F4EA',
  background: '#F4F7F6',
  surface: '#FFFFFF',
  text: '#111827',
  textMuted: '#6B7280',
  danger: '#E04B4B',
  dangerLight: '#FCE8E8',
  border: '#E5E7EB',
  white: '#FFFFFF',
  shadow: 'rgba(17, 24, 39, 0.05)',
};

// Compatibility aliases keep existing staff/admin screens on the same palette.
export const colors = {
  ...COLORS,
  primarySoft: COLORS.primaryLight,
  accent: '#D79A1E',
  warning: '#D79A1E',
  success: COLORS.primary,
  overlay: 'rgba(17, 24, 39, 0.55)',
  textPrimary: COLORS.text,
  textSecondary: COLORS.textMuted,
  textInverse: COLORS.white,
  textLow: COLORS.textMuted,
  textHigh: COLORS.text,
  dangerDark: '#B9363E',
  redSoft: COLORS.dangerLight,
  amberSoft: '#FFF4D6',
  blueSoft: '#E5F4FA',
  info: '#1684A7',
};
