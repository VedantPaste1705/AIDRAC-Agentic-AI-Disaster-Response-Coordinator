import { useState, useEffect, useCallback } from 'react';
import { userApi } from '../services/api';
import type { NearbyUser, NearbyUsersResponse, GeoPosition } from '../types';

interface UseNearbyUsersOptions {
  enabled?: boolean;
  refreshIntervalMs?: number;
  radiusKm?: number;
}

export function useNearbyUsers(
  position: GeoPosition | null,
  options: UseNearbyUsersOptions = {}
) {
  const { enabled = true, refreshIntervalMs = 30000, radiusKm = 10 } = options;
  const [users, setUsers] = useState<NearbyUser[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNearbyUsers = useCallback(async () => {
    if (!position || !enabled) return;

    setLoading(true);
    setError(null);

    try {
      const response = await userApi.getNearbyUsers(position.lat, position.lng, radiusKm);
      const data = response.data as NearbyUsersResponse;
      setUsers(data.users);
      setCount(data.count);
    } catch (err) {
      setError('Failed to fetch nearby users');
      console.error('Failed to fetch nearby users:', err);
    } finally {
      setLoading(false);
    }
  }, [position, enabled, radiusKm]);

  useEffect(() => {
    if (!enabled || !position) return;

    fetchNearbyUsers();

    const interval = setInterval(fetchNearbyUsers, refreshIntervalMs);

    return () => clearInterval(interval);
  }, [enabled, position, fetchNearbyUsers, refreshIntervalMs]);

  return { users, count, loading, error, refetch: fetchNearbyUsers };
}