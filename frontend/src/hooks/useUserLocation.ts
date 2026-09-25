import { useEffect, useRef, useCallback } from 'react';
import { userApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { GeoPosition } from '../types';

interface UseUserLocationOptions {
  enabled?: boolean;
  updateIntervalMs?: number;
  minDistanceMeters?: number;
  minAccuracyMeters?: number;
}

export function useUserLocation(
  position: GeoPosition | null,
  options: UseUserLocationOptions = {}
) {
  const {
    enabled = true,
    updateIntervalMs = 30000,
    minDistanceMeters = 50,
    minAccuracyMeters = 100,
  } = options;
  const { user, token } = useAuth();
  const lastSentPosition = useRef<GeoPosition | null>(null);
  const intervalRef = useRef<number | null>(null);

  const sendLocation = useCallback(async () => {
    if (!position || !user || !token) return;

    if (position.accuracy > minAccuracyMeters) {
      console.debug('Location accuracy too low:', position.accuracy);
      return;
    }

    if (lastSentPosition.current) {
      const dx = position.lat - lastSentPosition.current.lat;
      const dy = position.lng - lastSentPosition.current.lng;
      const distanceMeters = Math.sqrt(dx * dx + dy * dy) * 111000;
      if (distanceMeters < minDistanceMeters) return;
    }

    const now = Date.now();
    if (now - position.timestamp > 30000) {
      console.debug('Location timestamp too old:', now - position.timestamp);
      return;
    }

    try {
      await userApi.updateLocation({
        latitude: position.lat,
        longitude: position.lng,
        accuracy: position.accuracy,
        timestamp: position.timestamp,
      });
      lastSentPosition.current = { ...position };
    } catch (error) {
      console.error('Failed to update user location:', error);
    }
  }, [position, user, token, minDistanceMeters, minAccuracyMeters]);

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