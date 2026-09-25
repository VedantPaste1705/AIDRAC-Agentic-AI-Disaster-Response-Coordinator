import { useState, useEffect, useRef, useCallback } from 'react';
import type { GeolocationState, GeoPosition } from '../types';

interface UseGeolocationOptions {
  enableHighAccuracy?: boolean;
  timeout?: number;
  maximumAge?: number;
  watch?: boolean;
  staleThresholdMs?: number;
}

const defaults: UseGeolocationOptions = {
  enableHighAccuracy: true,
  timeout: 15000,
  maximumAge: 0,
  watch: true,
  staleThresholdMs: 30000,
};

export function useGeolocation(options: UseGeolocationOptions = {}): GeolocationState & {
  refresh: () => void;
  requestPermission: () => Promise<PermissionState>;
} {
  const opts = { ...defaults, ...options };
  const [state, setState] = useState<GeolocationState>({
    position: null,
    error: null,
    loading: true,
    permissionDenied: false,
    unsupported: false,
    permissionState: 'prompt',
  });
  const watchId = useRef<number | null>(null);
  const isMounted = useRef(true);

  const handleSuccess = useCallback((pos: GeolocationPosition) => {
    if (!isMounted.current) return;

    const position: GeoPosition = {
      lat: pos.coords.latitude,
      lng: pos.coords.longitude,
      accuracy: pos.coords.accuracy,
      timestamp: pos.timestamp,
    };

    const isStale = Date.now() - pos.timestamp > opts.staleThresholdMs!;

    setState({
      position,
      error: isStale ? 'Location data is stale' : null,
      loading: false,
      permissionDenied: false,
      unsupported: false,
      permissionState: 'granted',
    });
  }, [opts.staleThresholdMs]);

  const handleError = useCallback((err: GeolocationPositionError) => {
    if (!isMounted.current) return;

    setState((prev) => ({
      ...prev,
      loading: false,
      error:
        err.code === err.PERMISSION_DENIED
          ? 'Location permission denied'
          : err.code === err.TIMEOUT
          ? 'Location request timed out'
          : 'Location unavailable',
      permissionDenied: err.code === err.PERMISSION_DENIED,
      unsupported: false,
      permissionState: err.code === err.PERMISSION_DENIED ? 'denied' : 'prompt',
    }));
  }, []);

  const startWatching = useCallback(() => {
    if (!navigator.geolocation) {
      setState({
        position: null,
        error: 'Geolocation not supported by this browser',
        loading: false,
        permissionDenied: false,
        unsupported: true,
        permissionState: 'denied',
      });
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));

    if (opts.watch) {
      watchId.current = navigator.geolocation.watchPosition(
        handleSuccess,
        handleError,
        { enableHighAccuracy: opts.enableHighAccuracy, timeout: opts.timeout, maximumAge: opts.maximumAge }
      );
    } else {
      navigator.geolocation.getCurrentPosition(
        handleSuccess,
        handleError,
        { enableHighAccuracy: opts.enableHighAccuracy, timeout: opts.timeout, maximumAge: opts.maximumAge }
      );
    }
  }, [opts.watch, opts.enableHighAccuracy, opts.timeout, opts.maximumAge, handleSuccess, handleError]);

  const requestPermission = useCallback(async (): Promise<PermissionState> => {
    if (!navigator.permissions) {
      return 'prompt';
    }
    try {
      const permission = await navigator.permissions.query({ name: 'geolocation' });
      setState((prev) => ({ ...prev, permissionState: permission.state }));
      return permission.state;
    } catch {
      return 'prompt';
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    startWatching();

    if (navigator.permissions) {
      navigator.permissions.query({ name: 'geolocation' }).then((permission) => {
        if (isMounted.current) {
          setState((prev) => ({ ...prev, permissionState: permission.state }));
        }
        permission.onchange = () => {
          if (isMounted.current) {
            setState((prev) => ({ ...prev, permissionState: permission.state }));
          }
        };
      });
    }

    return () => {
      isMounted.current = false;
      if (watchId.current !== null) {
        navigator.geolocation.clearWatch(watchId.current);
      }
    };
  }, [startWatching]);

  return { ...state, refresh: startWatching, requestPermission };
}