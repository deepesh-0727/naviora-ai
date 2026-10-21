import { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { apiClient, buildApiUrl } from '../../shared/services/api';

export interface AdminMetrics {
  kpis: Record<string, number | string | null>;
  charts: Record<string, unknown>;
  alerts: Record<string, unknown>;
}

export function useAdminMetrics() {
  const [data, setData] = useState<AdminMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    setUnavailable(null);
    const paths = [
      buildApiUrl('admin', '/dashboard/kpis'),
      buildApiUrl('admin', '/dashboard/charts'),
      buildApiUrl('admin', '/dashboard/alerts'),
    ] as const;
    try {
      const [kpis, charts, alerts] = await Promise.all(paths.map(path => apiClient.get<Record<string, unknown>>(path)));
      const metricData: Record<string, number | string | null> = {};
      for (const [key, value] of Object.entries(kpis.data)) {
        if (value === null || typeof value === 'string' || typeof value === 'number') metricData[key] = value;
      }
      setData({ kpis: metricData, charts: charts.data, alerts: alerts.data });
    } catch (cause) {
      if (isAxiosError(cause) && (cause.response?.status === 404 || cause.response?.status === 501)) {
        setUnavailable(isAxiosError(cause) && typeof cause.config?.url === 'string' ? cause.config.url : paths[0]);
      } else if (isAxiosError(cause) && cause.response?.status === 500) {
        setError('The server could not load administration data. Check the backend database logs and try again.');
      } else setError('Could not load administration metrics.');
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void reload(); }, [reload]);
  return { data, loading, error, unavailable, reload };
}
