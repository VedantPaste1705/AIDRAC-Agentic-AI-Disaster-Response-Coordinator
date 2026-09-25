import { MapPin, Crosshair, AlertCircle, Clock } from 'lucide-react';
import type { GeolocationState } from '../types';

interface LocationStatusProps {
  geolocation: GeolocationState & { refresh: () => void; requestPermission: () => Promise<PermissionState> };
  showDetails?: boolean;
}

export default function LocationStatus({ geolocation, showDetails = false }: LocationStatusProps) {
  const { position, error, loading, permissionDenied, unsupported, permissionState } = geolocation;

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-on-surface-variant">
        <Crosshair className="h-4 w-4 animate-spin" />
        Acquiring GPS...
      </div>
    );
  }

  if (unsupported) {
    return (
      <div className="flex items-center gap-2 text-sm text-yellow-600" title="Geolocation not supported">
        <AlertCircle className="h-4 w-4" />
        GPS not supported
      </div>
    );
  }

  if (permissionDenied) {
    return (
      <div className="flex items-center gap-2 text-sm text-danger-500" title="Location permission denied">
        <AlertCircle className="h-4 w-4" />
        No GPS permission
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-sm text-secondary-500" title={error}>
        <AlertCircle className="h-4 w-4" />
        {error}
      </div>
    );
  }

  if (position) {
    const isStale = Date.now() - position.timestamp > 30000;
    const accuracyText = position.accuracy ? `±${Math.round(position.accuracy)}m` : 'accuracy unknown';
    const ageSeconds = Math.round((Date.now() - position.timestamp) / 1000);
    const ageText = ageSeconds < 60 ? `${ageSeconds}s ago` : `${Math.round(ageSeconds / 60)}m ago`;

    return (
      <div className="flex items-center gap-2 text-sm">
        <MapPin className={`h-4 w-4 ${isStale ? 'text-yellow-500' : 'text-success-700'}`} />
        <div className="flex flex-col">
          <span className={`${isStale ? 'text-yellow-500' : 'text-success-700'}`}>
            {position.lat.toFixed(4)}, {position.lng.toFixed(4)}
          </span>
          {showDetails && (
            <span className="text-[10px] font-mono text-on-surface-variant">
              {accuracyText} • {ageText} • {permissionState}
            </span>
          )}
          {isStale && !showDetails && (
            <span className="ml-1" title="Location data is stale">
              <Clock className="h-3 w-3 text-yellow-500" />
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm text-on-surface-variant">
      <Crosshair className="h-4 w-4" />
      No location
    </div>
  );
}