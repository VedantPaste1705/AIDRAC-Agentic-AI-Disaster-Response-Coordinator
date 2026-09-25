import { useEffect, useRef, useCallback } from 'react';
import { userApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { GeoPosition } from '../types';

interface UseUserLocationOptions {
  enabled?: boolean;
  updateIntervalMs?: number;
  minDistanceMeters?: number;
}

export function useUserLocation(
  position: GeoPosition | null,
  options: UseUserLocationOptions = {}
) {
  const { enabled = true, updateIntervalMs = 30000, minDistanceMeters = 50 } = options;
  const { user, token } = useAuth();
  const lastSentPosition = useRef<GeoPosition | null>(null);
  const intervalRef = useRef<number | null>(null);

  const sendLocation = useCallback(async () => {
    if (!position || !user || !token) return;

    if (lastSentPosition.current) {
      const dx = position.lat - lastSentPosition.current.lat;
      const dy = position.lng - lastSentPosition.current.lng;
      const distanceMeters = Math.sqrt(dx * dx + dy * dy) * 111000;
      if (distanceMeters < minDistanceMeters) return;
    }

    try {
      await userApi.updateLocation({
        latitude: position.lat,
        longitude: position.lng,
        accuracy: 0,
      });
      lastSentPosition.current = { ...position };
    } catch (error) {
      console.error('Failed to update user location:', error);
    }
  }, [position, user, token, minDistanceMeters]);

  useEffect(() => {
    if (!enabled || !position) return;

    sendLocation();

    intervalRef.current = window.setInterval(sendLocation, updateIntervalMs);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
      }
    };
  }, [enabled, position, sendLocation, updateIntervalMs]);

  return { sendLocation };
}