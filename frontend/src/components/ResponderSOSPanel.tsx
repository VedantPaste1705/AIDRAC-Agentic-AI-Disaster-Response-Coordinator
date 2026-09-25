import { useState, useCallback, useEffect } from 'react';
import { Shield, Navigation, UserCheck, MapPin, Clock, AlertTriangle, Check, X, ChevronDown, ChevronUp } from 'lucide-react';
import { sosApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useSettings } from '../context/SettingsContext';
import { useGeolocation } from '../hooks/useGeolocation';
import type { SOSIncident, SOSStatus, GeoPosition } from '../types';
import MaterialIcon from './ui/MaterialIcon';
import Card from './ui/Card';
import Button from './ui/Button';
import Badge from './ui/Badge';

const STATUS_STEPS: { status: SOSStatus; label: string; icon: React.ReactNode; color: string }[] = [
  { status: 'responder_accepted', label: 'Accepted', icon: <UserCheck className="h-4 w-4" />, color: 'text-success-400' },
  { status: 'assistance_in_progress', label: 'En Route', icon: <Navigation className="h-4 w-4" />, color: 'text-primary-400' },
  { status: 'assistance_provided', label: 'Helping', icon: <Shield className="h-4 w-4" />, color: 'text-warning-400' },
  { status: 'user_confirmed_safe', label: 'Confirmed Safe', icon: <Check className="h-4 w-4" />, color: 'text-green-400' },
];

const STATUS_COLORS: Record<SOSStatus, string> = {
  active: 'bg-danger-500/20 border-danger-500/30 text-danger-400',
  received: 'bg-danger-500/20 border-danger-500/30 text-danger-400',
  acknowledged: 'bg-warning-500/20 border-warning-500/30 text-warning-400',
  awaiting_responder: 'bg-warning-500/20 border-warning-500/30 text-warning-400',
  responder_assigned: 'bg-primary-500/20 border-primary-500/30 text-primary-400',
  responder_accepted: 'bg-success-500/20 border-success-500/30 text-success-400',
  assistance_in_progress: 'bg-primary-500/20 border-primary-500/30 text-primary-400',
  assistance_provided: 'bg-success-500/20 border-success-500/30 text-success-400',
  user_confirmed_safe: 'bg-success-500/20 border-success-500/30 text-success-400',
  cancelled: 'bg-slate-500/20 border-slate-500/30 text-slate-400',
  resolved: 'bg-success-500/20 border-success-500/30 text-success-400',
};

const STATUS_LABELS: Record<SOSStatus, string> = {
  active: 'Active',
  received: 'Received',
  acknowledged: 'Acknowledged',
  awaiting_responder: 'Awaiting Responder',
  responder_assigned: 'Responder Assigned',
  responder_accepted: 'Responder Accepted',
  assistance_in_progress: 'Assistance In Progress',
  assistance_provided: 'Assistance Provided',
  user_confirmed_safe: 'User Confirmed Safe',
  cancelled: 'Cancelled',
  resolved: 'Resolved',
};

interface ResponderSOSPanelProps {
  sos: SOSIncident;
  onClose: () => void;
  onStatusUpdate: (status: SOSStatus) => Promise<void>;
}

export default function ResponderSOSPanel({ sos, onClose, onStatusUpdate }: ResponderSOSPanelProps) {
  const { settings } = useSettings();
  const geolocation = useGeolocation({ watch: true });
  const position = geolocation.position;

  const [expanded, setExpanded] = useState(true);
  const [showMap, setShowMap] = useState(false);

  const currentStepIndex = STATUS_STEPS.findIndex(s => s.status === sos.status);
  const nextStatus = currentStepIndex >= 0 && currentStepIndex < STATUS_STEPS.length - 1 
    ? STATUS_STEPS[currentStepIndex + 1].status 
    : null;

  const canProgress = nextStatus !== null && (
    sos.status === 'responder_accepted' && nextStatus === 'assistance_in_progress' ||
    sos.status === 'assistance_in_progress' && nextStatus === 'assistance_provided' ||
    sos.status === 'assistance_provided' && nextStatus === 'user_confirmed_safe'
  );

  const handleProgress = async () => {
    if (!canProgress || !nextStatus) return;
    await onStatusUpdate(nextStatus);
  };

  const navigateToVictim = () => {
    if (position) {
      window.open(`/map?dest=${sos.latitude},${sos.longitude}&type=sos`, '_blank');
    }
  };

  const isResolved = ['user_confirmed_safe', 'resolved', 'cancelled'].includes(sos.status);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background">
      {/* Top Bar */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/40 hover:bg-slate-700/50 text-slate-400 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
          <div className="p-2 rounded-lg bg-primary-500/20 border border-primary-500/30">
            <Shield className="h-5 w-5 text-primary-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">ACTIVE SOS RESPONSE</h2>
            <p className="text-sm text-slate-400">You are assigned as a community responder</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="info" size="md">RESPONDER</Badge>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/40 hover:bg-slate-700/50 text-slate-400 hover:text-white transition-colors"
          >
            {expanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className={`flex-1 overflow-y-auto p-4 space-y-4 transition-all duration-300 ${expanded ? '' : 'hidden'}`}>
        {/* Status Progress Indicator */}
        <Card variant="glass" padding="md">
          <h3 className="text-sm font-mono text-slate-400 uppercase tracking-widest mb-4">Response Progress</h3>
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {STATUS_STEPS.map((step, index) => {
              const isCompleted = index < currentStepIndex;
              const isCurrent = index === currentStepIndex;
              const isFuture = index > currentStepIndex;

              return (
                <div key={step.status} className="flex items-center gap-2 shrink-0">
                  <div className="flex flex-col items-center gap-1">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${
                      isCompleted ? 'bg-success-500 border-success-500' :
                      isCurrent ? 'bg-primary-500 border-primary-500' :
                      'bg-slate-700 border-slate-600'
                    }`}>
                      {step.icon}
                    </div>
                    <span className={`text-xs font-mono text-center max-w-[80px] ${
                      isCompleted ? 'text-success-400' :
                      isCurrent ? 'text-primary-400' :
                      'text-slate-500'
                    }`}>
                      {step.label}
                    </span>
                  </div>
                  {index < STATUS_STEPS.length - 1 && (
                    <div className={`w-16 h-0.5 rounded ${
                      isCompleted ? 'bg-success-500' : 'bg-slate-700'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
        </Card>

        {/* SOS Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card variant="glass" padding="md">
            <h3 className="text-sm font-mono text-slate-400 uppercase tracking-widest mb-3">Victim Information</h3>
            <div className="space-y-3">
              <div>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Name</p>
                <p className="text-white font-medium">{sos.reporting_user_name || `User #${sos.reporting_user_id}`}</p>
              </div>
              <div>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Status</p>
                <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-mono uppercase tracking-wider ${STATUS_COLORS[sos.status] || 'bg-slate-800/50 border-slate-700/50'}`}>
                  {STATUS_LABELS[sos.status]}
                </span>
              </div>
              {sos.emergency_type && (
                <div>
                  <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Emergency Type</p>
                  <p className="text-white font-medium">{sos.emergency_type}</p>
                </div>
              )}
              {sos.emergency_details && (
                <div>
                  <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Details</p>
                  <p className="text-sm text-slate-300">{sos.emergency_details}</p>
                </div>
              )}
            </div>
          </Card>

          <Card variant="glass" padding="md">
            <h3 className="text-sm font-mono text-slate-400 uppercase tracking-widest mb-3">Location & Timing</h3>
            <div className="space-y-3">
              <div>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Coordinates</p>
                <p className="text-white font-mono text-sm flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-primary-400" />
                  {sos.latitude.toFixed(6)}, {sos.longitude.toFixed(6)}
                  {sos.location_accuracy && (
                    <span className="text-xs text-slate-400">(±{Math.round(sos.location_accuracy)}m)</span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Reported</p>
                <p className="text-white font-mono text-sm">{new Date(sos.created_at).toLocaleString()}</p>
              </div>
              {sos.accepted_at && (
                <div>
                  <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Accepted</p>
                  <p className="text-white font-mono text-sm">{new Date(sos.accepted_at).toLocaleString()}</p>
                </div>
              )}
              {sos.updated_at && (
                <div>
                  <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Last Update</p>
                  <p className="text-white font-mono text-sm">{new Date(sos.updated_at).toLocaleString()}</p>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Action Buttons */}
        <Card variant="glass" padding="md" className={isResolved ? 'bg-success-500/5 border-success-500/20' : ''}>
          <h3 className="text-sm font-mono text-slate-400 uppercase tracking-widest mb-3">
            {isResolved ? 'Incident Resolved' : 'Response Actions'}
          </h3>
          <div className="space-y-2">
            {isResolved ? (
              <div className="p-3 rounded-lg bg-success-500/10 border border-success-500/30 text-success-400 text-center">
                <Check className="h-6 w-6 mx-auto mb-2" />
                <p className="font-medium">SOS Resolved - Victim confirmed safe</p>
                <p className="text-xs text-slate-400 mt-1">This panel will close automatically</p>
              </div>
            ) : (
              <>
                {canProgress && nextStatus && (
                  <Button
                    onClick={handleProgress}
                    className="w-full py-3 rounded-lg bg-primary-600 text-white font-medium hover:bg-primary-500 transition-colors flex items-center justify-center gap-2"
                  >
                    {STATUS_STEPS.find(s => s.status === nextStatus)?.icon}
                    {STATUS_STEPS.find(s => s.status === nextStatus)?.label.toUpperCase()}
                  </Button>
                )}

                {position && (
                  <Button
                    onClick={navigateToVictim}
                    variant="secondary"
                    className="w-full py-3 rounded-lg flex items-center justify-center gap-2"
                  >
                    <Navigation className="h-4 w-4" />
                    Navigate to Victim
                  </Button>
                )}

                {!canProgress && !isResolved && (
                  <div className="p-3 rounded-lg bg-warning-500/10 border border-warning-500/30 text-warning-400 text-sm text-center">
                    <AlertTriangle className="h-5 w-5 mx-auto mb-2" />
                    <p className="font-medium">Waiting for next action</p>
                    <p className="text-xs mt-1">Current status: {STATUS_LABELS[sos.status]}</p>
                  </div>
                )}
              </>
            )}
          </div>
        </Card>

        {/* Quick Map Preview */}
        {showMap && position && (
          <Card variant="glass" padding="md">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-mono text-slate-400 uppercase tracking-widest">Navigation Preview</h3>
              <button
                onClick={() => setShowMap(false)}
                className="p-1.5 rounded hover:bg-white/5 transition-colors"
              >
                <X className="h-4 w-4 text-slate-400" />
              </button>
            </div>
            <iframe
              src={`/map?dest=${sos.latitude},${sos.longitude}&type=sos&origin=${position.lat},${position.lng}`}
              className="w-full h-[300px] rounded-lg border border-slate-700/40"
              title="Navigation to victim"
            />
          </Card>
        )}
      </div>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-slate-700/50 bg-slate-900/80 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full ${position ? 'bg-green-500' : 'bg-slate-500'}`} />
            <span className="text-sm text-slate-400">GPS {position ? 'Active' : 'Unavailable'}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={() => setShowMap(!showMap)}
              variant={showMap ? 'primary' : 'secondary'}
              size="sm"
            >
              {showMap ? 'Hide Map' : 'Show Map'}
            </Button>
            <Button onClick={onClose} variant="secondary" size="sm">
              Close Panel
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}