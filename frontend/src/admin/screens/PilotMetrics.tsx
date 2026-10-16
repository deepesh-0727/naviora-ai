import React, { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { Button, Card, Loader, ScreenContainer, SectionHeader } from '../../shared/components';
import { apiClient } from '../../shared/services/api';
import { colors } from '../../shared/theme/colors';

interface PilotMetricsResponse {
  period: { start: string; end: string };
  wait_time: { avg_minutes: number | null; p50: number | null; p95: number | null; sample_size: number };
  emergency_response: { avg_seconds: number | null; sample_size: number };
  no_show_rate: { rate: number | null; total: number; no_shows: number };
  voice_intents: {
    total: number;
    fallback_count: number;
    avg_confidence: number | null;
    reviewed_accuracy: number | null;
    reviewed_sample_size: number;
  };
  active_staff: { daily: number; weekly: number };
  uptime: { last_30d: number | null; source: string };
  patient_satisfaction: {
    nps: number | null;
    nps_responses: number;
    promoters: number;
    passives: number;
    detractors: number;
  };
}

interface MetricCardProps {
  title: string;
  value: string;
  detail: string;
  width: `${number}%`;
}

function MetricCard({ title, value, detail, width }: MetricCardProps) {
  return (
    <Card style={[styles.metricCard, { width }]}>
      <Text style={styles.metricTitle}>{title}</Text>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricDetail}>{detail}</Text>
    </Card>
  );
}

function formatMinutes(value: number | null): string {
  return value === null ? 'No data yet' : `${value.toFixed(1)} min`;
}

function formatPercent(value: number | null): string {
  return value === null ? 'No data yet' : `${(value * 100).toFixed(1)}%`;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return 'No data yet';
  const wholeSeconds = Math.round(seconds);
  const minutes = Math.floor(wholeSeconds / 60);
  const remainingSeconds = wholeSeconds % 60;
  return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`;
}

export default function PilotMetrics() {
  const { width: screenWidth } = useWindowDimensions();
  const [metrics, setMetrics] = useState<PilotMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [clockNow, setClockNow] = useState(Date.now());
  const requestInFlight = useRef(false);
  const hasLoaded = useRef(false);
  const columns = screenWidth >= 768 ? 2 : 1;
  const cardWidth: `${number}%` = columns === 2 ? '48%' : '100%';

  const loadMetrics = useCallback(async () => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setRefreshing(true);
    if (!hasLoaded.current) setLoading(true);
    setError(false);
    try {
      const response = await apiClient.get<PilotMetricsResponse>('/api/v1/admin/pilot/metrics');
      setMetrics(response.data);
      setLastUpdated(Date.now());
      setClockNow(Date.now());
      hasLoaded.current = true;
    } catch {
      setError(true);
    } finally {
      requestInFlight.current = false;
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadMetrics();
    const refreshTimer = setInterval(() => void loadMetrics(), 60_000);
    const clockTimer = setInterval(() => setClockNow(Date.now()), 1_000);
    return () => {
      clearInterval(refreshTimer);
      clearInterval(clockTimer);
    };
  }, [loadMetrics]);

  const updatedAgo = lastUpdated === null ? null : Math.floor((clockNow - lastUpdated) / 1_000);
  const waitHasSample = Boolean(metrics && metrics.wait_time.sample_size > 0);
  const emergencyHasSample = Boolean(metrics && metrics.emergency_response.sample_size > 0);
  const noShowHasSample = Boolean(metrics && metrics.no_show_rate.total > 0);
  const voiceHasReviewedSample = Boolean(metrics && metrics.voice_intents.reviewed_sample_size > 0);
  const npsHasSample = Boolean(metrics && metrics.patient_satisfaction.nps_responses > 0);

  return (
    <ScreenContainer style={styles.screen}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void loadMetrics()} tintColor={colors.primary} />}
      >
        <SectionHeader title="Pilot Metrics" />
        <Text style={styles.freshness}>
          {updatedAgo === null ? 'Last updated: —' : `Last updated: ${updatedAgo} second${updatedAgo === 1 ? '' : 's'} ago`}
        </Text>
        {error ? (
          <View style={styles.errorBanner}>
            <Text style={styles.errorText}>Failed to load metrics</Text>
            <Button title="Retry" variant="secondary" onPress={() => void loadMetrics()} />
          </View>
        ) : null}
        {loading ? (
          <View style={styles.cards}>
            {['Wait Time', 'Emergency Response', 'No-Show Rate', 'Voice Intent Accuracy', 'Active Staff', 'Uptime', 'Patient NPS'].map((title) => (
              <Card key={title} style={[styles.metricCard, { width: cardWidth }]}>
                <Text style={styles.metricTitle}>{title}</Text>
                <Loader message="Loading…" />
              </Card>
            ))}
          </View>
        ) : metrics ? (
          <View style={styles.cards}>
            <MetricCard
              title="Wait Time"
              value={waitHasSample ? formatMinutes(metrics.wait_time.avg_minutes) : 'No data yet'}
              detail={`p50: ${waitHasSample ? formatMinutes(metrics.wait_time.p50) : 'No data yet'} · p95: ${waitHasSample ? formatMinutes(metrics.wait_time.p95) : 'No data yet'} · n=${metrics.wait_time.sample_size}`}
              width={cardWidth}
            />
            <MetricCard
              title="Emergency Response"
              value={emergencyHasSample ? formatDuration(metrics.emergency_response.avg_seconds) : 'No data yet'}
              detail={`n=${metrics.emergency_response.sample_size}`}
              width={cardWidth}
            />
            <MetricCard
              title="No-Show Rate"
              value={noShowHasSample ? formatPercent(metrics.no_show_rate.rate) : 'No data yet'}
              detail={`${metrics.no_show_rate.no_shows} of ${metrics.no_show_rate.total} appointments`}
              width={cardWidth}
            />
            <MetricCard
              title="Voice Intent Accuracy"
              value={voiceHasReviewedSample ? formatPercent(metrics.voice_intents.reviewed_accuracy) : 'No data yet'}
              detail={`${metrics.voice_intents.total} total · ${metrics.voice_intents.fallback_count} fallbacks · confidence ${formatPercent(metrics.voice_intents.avg_confidence)}`}
              width={cardWidth}
            />
            <MetricCard
              title="Active Staff"
              value={String(metrics.active_staff.daily)}
              detail={`${metrics.active_staff.weekly} weekly`}
              width={cardWidth}
            />
            <MetricCard
              title="Uptime"
              value={metrics.uptime.last_30d === null ? 'External — see UptimeRobot' : formatPercent(metrics.uptime.last_30d)}
              detail={metrics.uptime.source === 'manual_uptimerobot_review' ? 'Review monitor history in UptimeRobot' : 'Last 30 days'}
              width={cardWidth}
            />
            <MetricCard
              title="Patient NPS"
              value={npsHasSample && metrics.patient_satisfaction.nps !== null ? `${metrics.patient_satisfaction.nps}` : 'No data yet'}
              detail={npsHasSample
                ? `Promoters: ${metrics.patient_satisfaction.promoters} · Passives: ${metrics.patient_satisfaction.passives} · Detractors: ${metrics.patient_satisfaction.detractors}`
                : 'No NPS responses yet'}
              width={cardWidth}
            />
          </View>
        ) : error ? null : (
          <Text style={styles.emptyText}>No data yet</Text>
        )}
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { padding: 16, paddingBottom: 28 },
  freshness: { color: colors.textMuted, marginTop: 4, marginBottom: 14 },
  cards: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 12 },
  metricCard: { marginBottom: 0 },
  metricTitle: { color: colors.textMuted, fontSize: 14, fontWeight: '600' },
  metricValue: { color: colors.text, fontSize: 26, fontWeight: '700', marginTop: 10 },
  metricDetail: { color: colors.textMuted, fontSize: 13, marginTop: 8 },
  errorBanner: { backgroundColor: '#FDECEC', borderColor: colors.danger, borderWidth: 1, borderRadius: 10, padding: 12, marginBottom: 14, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  errorText: { color: colors.danger, fontWeight: '700' },
  emptyText: { color: colors.textMuted, textAlign: 'center', marginTop: 24 },
});
