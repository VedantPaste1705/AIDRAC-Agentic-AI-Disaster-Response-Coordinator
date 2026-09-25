import { useState, useEffect, useCallback } from 'react';
import { sosApi } from '../services/api';
import type { GeoPosition, SOSNearbyResponse } from '../types';

interface UseNearbySOSOptions {
  enabled?: boolean;
  refreshIntervalMs?: number;
  radiusKm?: number;
}

export function useNearbySOS(
  position: GeoPosition | null,
  options: UseNearbySOSOptions = {}
) {
  const { enabled = true, refreshIntervalMs = 30000, radiusKm = 10 } = options;
  const [emergencies, setEmergencies] = useState<SOSNearbyResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNearbySOS = useCallback(async () => {
    if (!position || !enabled) return;

    setLoading(true);
    setError(null);

    try {
      const response = await sosApi.getNearby(position.lat, position.lng, radiusKm);
      const data = response.data as SOSNearbyResponse[];
      setEmergencies(data);
    } catch (err) {
      setError('Failed to fetch nearby emergencies');
      console.error('Failed to fetch nearby emergencies:', err);
    } finally {
      setLoading(false);
    }
  }, [position, enabled, radiusKm]);

  useEffect(() => {
    if (!enabled || !position) return;

    fetchNearbySOS();

    const interval = setInterval(fetchNearbySOS, refreshIntervalMs);

    return () => clearInterval(interval);
  }, [enabled, position, fetchNearbySOS, refreshIntervalMs]);

  return { emergencies, loading, error, refetch: fetchNearbySOS };
}