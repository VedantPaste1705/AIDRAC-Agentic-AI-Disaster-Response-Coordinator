import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Loader2, CheckCircle, XCircle, MapPin, Clock, UserCheck, Shield } from 'lucide-react';
import { useGeolocation } from '../hooks/useGeolocation';
import { sosApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { GeoPosition, SOSIncident, SOSStatus } from '../types';

interface SOSState {
  status: SOSStatus | 'idle' | 'requesting' | 'confirming' | 'sending' | 'success' | 'error';
  incident: SOSIncident | null;
  error: string | null;
}

const STATUS_LABELS: Record<SOSStatus, string> = {
  active: 'Emergency Active',
  received: 'Emergency Received',
  acknowledged: 'Help Being Coordinated',
  awaiting_responder: 'Looking for Responder',
  responder_assigned: 'Responder Assigned',
  responder_accepted: 'Responder Accepted',
  assistance_in_progress: 'Help On The Way',
  assistance_provided: 'Assistance Provided',
  user_confirmed_safe: 'Confirmed Safe',
  cancelled: 'Cancelled',
  resolved: 'Resolved',
};

const STATUS_ICONS: Record<SOSStatus, React.ElementType> = {
  active: AlertCircle,
  received: AlertCircle,
  acknowledged: Shield,
  awaiting_responder: UserCheck,
  responder_assigned: Shield,
  responder_accepted: CheckCircle,
  assistance_in_progress: MapPin,
  assistance_provided: CheckCircle,
  user_confirmed_safe: CheckCircle,
  cancelled: XCircle,
  resolved: CheckCircle,
};

const STATUS_COLORS: Record<SOSStatus, string> = {
  active: 'text-danger-500',
  received: 'text-danger-500',
  acknowledged: 'text-warning-500',
  awaiting_responder: 'text-warning-500',
  responder_assigned: 'text-primary-500',
  responder_accepted: 'text-success-500',
  assistance_in_progress: 'text-primary-500',
  assistance_provided: 'text-success-500',
  user_confirmed_safe: 'text-success-500',
  cancelled: 'text-slate-500',
  resolved: 'text-success-500',
};

export function useSOS() {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [sosState, setSosState] = useState<SOSState>({
    status: 'idle',
    incident: null,
    error: null,
  });

  const triggerSOS = useCallback(async () => {
    if (!user || !token) {
      setSosState({ status: 'error', incident: null, error: 'Not authenticated' });
      return;
    }

    setSosState({ status: 'requesting', incident: null, error: null });

    try {
      if (!navigator.geolocation) {
        throw new Error('Geolocation not supported');
      }

      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0,
        });
      });

      const sosPosition: GeoPosition = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp,
      };

      if (sosPosition.accuracy > 200) {
        setSosState({
          status: 'confirming',
          incident: null,
          error: `Low GPS accuracy (±${Math.round(sosPosition.accuracy)}m). Continue anyway?`,
        });
        return;
      }

      setSosState({ status: 'sending', incident: null, error: null });

      const response = await sosApi.create({
        title: 'SOS Emergency',
        message: `Emergency SOS from ${user.full_name}`,
        severity: 'critical',
        latitude: sosPosition.lat,
        longitude: sosPosition.lng,
        accuracy: sosPosition.accuracy,
        timestamp: sosPosition.timestamp,
        emergency_type: 'general',
        emergency_details: `Emergency SOS from ${user.full_name}`,
      });

      const incident = response.data as SOSIncident;
      setSosState({ status: 'active', incident, error: null });
    } catch (err: unknown) {
      let errorMessage = 'Failed to send SOS';
      if (err instanceof GeolocationPositionError) {
        switch (err.code) {
          case err.PERMISSION_DENIED:
            errorMessage = 'Location permission denied. Enable in browser settings.';
            break;
          case err.TIMEOUT:
            errorMessage = 'Location request timed out. Try again.';
            break;
          default:
            errorMessage = 'Unable to get current location.';
        }
      } else if (err instanceof Error && err.message) {
        errorMessage = err.message;
      }
      setSosState({ status: 'error', incident: null, error: errorMessage });
    }
  }, [user, token, navigate]);

  const confirmLowAccuracy = useCallback(async () => {
    if (sosState.status !== 'confirming') return;

    setSosState({ status: 'sending', incident: null, error: null });

    try {
      // We need to re-get the position since we didn't store it
      if (!navigator.geolocation) {
        throw new Error('Geolocation not supported');
      }

      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0,
        });
      });

      const sosPosition: GeoPosition = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp,
      };

      const response = await sosApi.create({
        title: 'SOS Emergency',
        message: `Emergency SOS from ${user?.full_name} (low accuracy)`,
        severity: 'critical',
        latitude: sosPosition.lat,
        longitude: sosPosition.lng,
        accuracy: sosPosition.accuracy,
        timestamp: sosPosition.timestamp,
        emergency_type: 'general',
        emergency_details: `Emergency SOS from ${user?.full_name} (low accuracy)`,
      });

      const incident = response.data as SOSIncident;
      setSosState({ status: 'active', incident, error: null });
    } catch {
      setSosState({ status: 'error', incident: null, error: 'Failed to send SOS' });
    }
  }, [sosState, user]);

  const cancelSOS = useCallback(async () => {
    if (sosState.incident) {
      try {
        await sosApi.cancel(sosState.incident.id);
      } catch {
        // Ignore cancellation errors
      }
    }
    setSosState({ status: 'idle', incident: null, error: null });
  }, [sosState.incident]);

  const confirmSafe = useCallback(async () => {
    if (!sosState.incident) return;
    try {
      await sosApi.confirmSafe(sosState.incident.id);
      setSosState(prev => ({ ...prev, incident: prev.incident ? { ...prev.incident, status: 'resolved' as SOSStatus } : null }));
      setTimeout(() => setSosState({ status: 'idle', incident: null, error: null }), 3000);
    } catch {
      // Error handled by polling
    }
  }, [sosState.incident]);

  // Poll for updates when SOS is active
  useEffect(() => {
    if (!sosState.incident || sosState.status !== 'active') return;

    const poll = async () => {
      try {
        const response = await sosApi.getById(sosState.incident!.id);
        const incident = response.data as SOSIncident;
        setSosState(prev => ({ ...prev, incident }));
        
        if (incident.status === 'resolved' || incident.status === 'cancelled') {
          setSosState(prev => ({ ...prev, status: incident.status }));
          setTimeout(() => setSosState({ status: 'idle', incident: null, error: null }), 5000);
        }
      } catch {
        // Ignore polling errors
      }
    };

    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, [sosState.incident, sosState.status]);

  return { sosState, triggerSOS, confirmLowAccuracy, cancelSOS, confirmSafe };
}

export default function EmergencyButton() {
  const { sosState, triggerSOS, confirmLowAccuracy, cancelSOS, confirmSafe } = useSOS();

  if (sosState.status === 'idle') {
    return (
      <button
        onClick={triggerSOS}
        className="w-full flex items-center justify-center gap-2 bg-danger-600 text-white px-5 py-3 rounded-xl shadow-[0_0_15px_rgba(220,38,38,0.4)] hover:bg-danger-500 transition-all hover:scale-[1.02] active:scale-95 cursor-pointer relative overflow-hidden group"
      >
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]"></div>
        <AlertCircle className="h-5 w-5" />
        <span className="font-bold tracking-wide">Emergency SOS</span>
      </button>
    );
  }

  if (sosState.status === 'requesting') {
    return (
      <div className="w-full flex flex-col items-center gap-3 p-4 bg-slate-900/90 border border-danger-500/30 rounded-xl">
        <Loader2 className="h-8 w-8 text-danger-500 animate-spin" />
        <p className="text-white font-medium">Getting precise location...</p>
        <p className="text-xs text-slate-400 text-center">Please wait</p>
      </div>
    );
  }

  if (sosState.status === 'confirming') {
    return (
      <div className="w-full flex flex-col items-center gap-3 p-4 bg-slate-900/90 border border-yellow-500/30 rounded-xl">
        <AlertCircle className="h-8 w-8 text-yellow-500" />
        <p className="text-white font-medium">Low GPS Accuracy</p>
        <p className="text-xs text-slate-400 text-center">{sosState.error}</p>
        <div className="flex gap-2 w-full">
          <button
            onClick={confirmLowAccuracy}
            className="flex-1 bg-danger-600 text-white py-2 rounded-lg font-medium hover:bg-danger-500"
          >
            Send Anyway
          </button>
          <button
            onClick={cancelSOS}
            className="flex-1 bg-slate-700 text-white py-2 rounded-lg font-medium hover:bg-slate-600"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  if (sosState.status === 'sending') {
    return (
      <div className="w-full flex flex-col items-center gap-3 p-4 bg-slate-900/90 border border-primary-500/30 rounded-xl">
        <Loader2 className="h-8 w-8 text-primary-500 animate-spin" />
        <p className="text-white font-medium">Sending emergency alert...</p>
      </div>
    );
  }

  if (sosState.status === 'error') {
    return (
      <div className="w-full flex flex-col items-center gap-3 p-4 bg-slate-900/90 border border-danger-500/30 rounded-xl">
        <XCircle className="h-8 w-8 text-danger-500" />
        <p className="text-white font-medium">Failed to Send SOS</p>
        <p className="text-xs text-danger-400 text-center">{sosState.error}</p>
        <button
          onClick={cancelSOS}
          className="bg-slate-700 text-white px-4 py-2 rounded-lg font-medium hover:bg-slate-600"
        >
          Dismiss
        </button>
      </div>
    );
  }

  // Active SOS state
  const incident = sosState.incident;
  const status = incident?.status as SOSStatus || 'active';
  const StatusIcon = STATUS_ICONS[status] || AlertCircle;
  const statusColor = STATUS_COLORS[status] || 'text-danger-500';
  const statusLabel = STATUS_LABELS[status] || 'Emergency Active';

  return (
    <div className="w-full flex flex-col gap-3 p-4 bg-slate-900/90 border border-danger-500/30 rounded-xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusIcon className={`h-8 w-8 ${statusColor}`} />
          <div>
            <p className="text-white font-medium text-lg">Emergency SOS Activated</p>
            <p className="text-xs text-slate-400">{statusLabel}</p>
          </div>
        </div>
        {incident && incident.status !== 'resolved' && incident.status !== 'cancelled' && (
          <button
            onClick={cancelSOS}
            className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded"
          >
            Cancel SOS
          </button>
        )}
      </div>

      {incident && (
        <div className="space-y-2 text-xs border-t border-slate-700 pt-3">
          <div className="flex items-center gap-2 text-slate-400">
            <Clock className="h-3 w-3" />
            <span>Created: {new Date(incident.created_at).toLocaleTimeString()}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <MapPin className="h-3 w-3" />
            <span>
              Location: {incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}
              {incident.location_accuracy && ` (±${Math.round(incident.location_accuracy)}m)`}
            </span>
          </div>
          {incident.emergency_type && (
            <div className="flex items-center gap-2 text-slate-400">
              <Shield className="h-3 w-3" />
              <span>Type: {incident.emergency_type}</span>
            </div>
          )}
          
          {incident.assigned_responder_id && (
            <div className="flex items-center gap-2 text-success-500 border-t border-slate-700 pt-2">
              <UserCheck className="h-3 w-3" />
              <span>Responder assigned: {incident.assigned_responder_name || 'User #' + incident.assigned_responder_id}</span>
            </div>
          )}

          {incident.status === 'assistance_provided' && (
            <div className="flex items-center gap-2 text-warning-500 border-t border-slate-700 pt-2">
              <AlertCircle className="h-3 w-3" />
              <span>Assistance provided - confirm your safety</span>
            </div>
          )}

          {incident.status === 'user_confirmed_safe' && (
            <div className="flex items-center gap-2 text-success-500 border-t border-slate-700 pt-2">
              <CheckCircle className="h-3 w-3" />
              <span>You are safe. SOS resolved.</span>
            </div>
          )}
        </div>
      )}

      {incident && incident.status === 'assistance_provided' && (
        <div className="flex gap-2">
          <button
            onClick={confirmSafe}
            className="flex-1 bg-success-600 text-white py-2 rounded-lg font-medium hover:bg-success-500"
          >
            Yes, I'm Safe
          </button>
          <button
            onClick={cancelSOS}
            className="flex-1 bg-danger-600 text-white py-2 rounded-lg font-medium hover:bg-danger-500"
          >
            Still Need Help
          </button>
        </div>
      )}
    </div>
  );
}