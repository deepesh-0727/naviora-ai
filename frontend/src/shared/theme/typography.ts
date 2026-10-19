import { COLORS } from './colors';

export const typography = {
  title: { fontSize: 24, fontWeight: '700' as const },
  subtitle: { fontSize: 18, fontWeight: '600' as const },
  body: { fontSize: 14, fontWeight: '400' as const },
  label: { fontSize: 12, fontWeight: '600' as const },
};

export const RADIUS = { sm: 8, md: 12, lg: 16, xl: 24, full: 999 } as const;

export const TYPO = {
  h1: { fontSize: 26, fontWeight: '800' as const, color: COLORS.text },
  h2: { fontSize: 20, fontWeight: '700' as const, color: COLORS.text },
  h3: { fontSize: 16, fontWeight: '700' as const, color: COLORS.text },
  body: { fontSize: 14, color: COLORS.text },
  bodyMuted: { fontSize: 14, color: COLORS.textMuted },
  caption: { fontSize: 12, color: COLORS.textMuted },
};
