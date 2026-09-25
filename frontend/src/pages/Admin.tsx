import MaterialIcon from '../components/ui/MaterialIcon';
import DashboardCard from '../components/DashboardCard';
import StatusBadge from '../components/ui/StatusBadge';
import Card from '../components/ui/Card';
import SectionHeader from '../components/ui/SectionHeader';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import { shelterApi, hospitalApi, disasterApi, sosApi } from '../services/api';
import { Shelter, Hospital, Disaster, SOSAdminListResponse, SOSStatus, SOSResponderType } from '../types';
import { AlertTriangle, Navigation, UserCheck, Shield, MapPin, Clock, User } from 'lucide-react';

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

const RESPONDER_TYPE_LABELS: Record<SOSResponderType, string> = {
  community: 'Community Responder',
  official: 'Official Responder',
};

function SOSActiveIncidents() {
  const { data: incidents, loading, refetch } = useApi<SOSAdminListResponse[]>(() => sosApi.adminGetActive());

  if (loading) return <LoadingSpinner size="sm" className="mx-auto my-4" />;

  if (!incidents || incidents.length === 0) {
    return (
      <div className="flex items-center gap-3 py-5 text-base text-slate-500">
        <AlertTriangle className="text-success-500" />
        No active SOS incidents
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {incidents.map((sos) => (
        <div key={sos.id} className={`p-4 rounded-lg border ${STATUS_COLORS[sos.status as SOSStatus] || 'bg-slate-800/50 border-slate-700/50'}`}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-mono text-slate-400">SOS #{sos.id}</span>
                <span className="px-2 py-1 rounded text-xs font-mono uppercase tracking-wider" style={{ backgroundColor: STATUS_COLORS[sos.status as SOSStatus] }}>
                  {STATUS_LABELS[sos.status as SOSStatus]}
                </span>
                {sos.responder_type && (
                  <span className="px-2 py-1 rounded text-xs font-mono bg-slate-700/50 border border-slate-600">
                    {RESPONDER_TYPE_LABELS[sos.responder_type as SOSResponderType]}
                  </span>
                )}
              </div>
              <div className="mt-2 flex flex-wrap gap-4 text-sm text-slate-300">
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3" />
                  {sos.reporting_user_name || `User #${sos.reporting_user_id}`}
                </span>
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {sos.latitude.toFixed(4)}, {sos.longitude.toFixed(4)}
                  {sos.location_accuracy && ` (\u00B1${Math.round(sos.location_accuracy)}m)`}
                </span>
                {sos.emergency_type && (
                  <span className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    {sos.emergency_type}
                  </span>
                )}
                {sos.assigned_responder_name && (
                  <span className="flex items-center gap-1 text-success-400">
                    <UserCheck className="h-3 w-3" />
                    Responder: {sos.assigned_responder_name}
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-col items-end gap-2 shrink-0">
              <span className="text-xs text-slate-500">
                Created: {new Date(sos.created_at).toLocaleString()}
              </span>
              {sos.accepted_at && (
                <span className="text-xs text-slate-500">
                  Accepted: {new Date(sos.accepted_at).toLocaleString()}
                </span>
              )}
              {sos.resolved_at && (
                <span className="text-xs text-slate-500">
                  Resolved: {new Date(sos.resolved_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function SOSIncidentHistory() {
  const { data: incidents, loading, refetch } = useApi<SOSAdminListResponse[]>(() => sosApi.adminGetHistory({ limit: 50 }));

  if (loading) return <LoadingSpinner size="sm" className="mx-auto my-4" />;

  if (!incidents || incidents.length === 0) {
    return (
      <div className="flex items-center gap-3 py-5 text-base text-slate-500">
        <AlertTriangle className="text-slate-500" />
        No resolved SOS incidents
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {incidents.map((sos) => (
        <div key={sos.id} className={`p-4 rounded-lg border ${STATUS_COLORS[sos.status as SOSStatus] || 'bg-slate-800/50 border-slate-700/50'}`}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-mono text-slate-400">SOS #{sos.id}</span>
                <span className="px-2 py-1 rounded text-xs font-mono uppercase tracking-wider" style={{ backgroundColor: STATUS_COLORS[sos.status as SOSStatus] }}>
                  {STATUS_LABELS[sos.status as SOSStatus]}
                </span>
                {sos.responder_type && (
                  <span className="px-2 py-1 rounded text-xs font-mono bg-slate-700/50 border border-slate-600">
                    {RESPONDER_TYPE_LABELS[sos.responder_type as SOSResponderType]}
                  </span>
                )}
              </div>
              <div className="mt-2 flex flex-wrap gap-4 text-sm text-slate-300">
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3" />
                  {sos.reporting_user_name || `User #${sos.reporting_user_id}`}
                </span>
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {sos.latitude.toFixed(4)}, {sos.longitude.toFixed(4)}
                </span>
                {sos.assigned_responder_name && (
                  <span className="flex items-center gap-1 text-success-400">
                    <UserCheck className="h-3 w-3" />
                    Responder: {sos.assigned_responder_name}
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-col items-end gap-2 shrink-0">
              <span className="text-xs text-slate-500">
                Created: {new Date(sos.created_at).toLocaleString()}
              </span>
              {sos.accepted_at && (
                <span className="text-xs text-slate-500">
                  Accepted: {new Date(sos.accepted_at).toLocaleString()}
                </span>
              )}
              {sos.resolved_at && (
                <span className="text-xs text-slate-500">
                  Resolved: {new Date(sos.resolved_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Admin() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const { data: shelters, loading: sheltersLoading } = useApi<Shelter[]>(() => shelterApi.getAll());
  const { data: hospitals, loading: hospitalsLoading } = useApi<Hospital[]>(() => hospitalApi.getAll());
  const { data: disasters, loading: disastersLoading } = useApi<Disaster[]>(() => disasterApi.getAll());

  const loading = sheltersLoading || hospitalsLoading || disastersLoading;

  if (loading) return <LoadingSpinner />;

  const activeDisasters = disasters?.filter((d) => d.status === 'active').length ?? 0;
  const totalCapacity = shelters?.reduce((sum, s) => sum + s.capacity, 0) ?? 0;
  const totalOccupancy = shelters?.reduce((sum, s) => sum + s.occupancy, 0) ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <div className="p-3 bg-primary-500/10 border border-primary-500/20 rounded-xl shadow-[0_0_15px_rgba(37,99,235,0.2)]">
          <MaterialIcon icon="admin_panel_settings" className="text-3xl text-primary-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold font-display text-white tracking-tight">Admin Console</h1>
          <p className="text-sm font-mono text-slate-400 uppercase tracking-widest mt-1">System Overview & Management</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DashboardCard
          title="Total Shelters"
          value={shelters?.length ?? 0}
          icon="emergency_home"
          subtitle={`${totalOccupancy}/${totalCapacity} occupied`}
          color="blue"
        />
        <DashboardCard
          title="Total Hospitals"
          value={hospitals?.length ?? 0}
          icon="local_hospital"
          subtitle={`${hospitals?.filter((h) => h.emergency_available).length ?? 0} emergency ready`}
          color="green"
        />
        <DashboardCard
          title="Active Disasters"
          value={activeDisasters}
          icon="warning"
          subtitle={`${disasters?.length ?? 0} total incidents`}
          color="red"
        />
        <DashboardCard
          title="System Status"
          value="Operational"
          icon="dns"
          subtitle="All systems online"
          color="green"
        />
      </div>

      {/* ===== SOS: Active Incidents ===== */}
      {isAdmin && (
        <Card variant="glass" padding="md">
          <SectionHeader title="Active SOS Incidents" />
          <SOSActiveIncidents />
        </Card>
      )}

      {/* ===== SOS: Incident History ===== */}
      {isAdmin && (
        <Card variant="glass" padding="md">
          <SectionHeader title="SOS Incident History" />
          <SOSIncidentHistory />
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card variant="glass" padding="md">
          <SectionHeader title="Shelter Overview" />
          {shelters && shelters.length > 0 ? (
            <div className="overflow-x-auto mt-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50 text-sm font-mono uppercase tracking-widest text-slate-400">
                    <th className="text-left py-3 px-4">Name</th>
                    <th className="text-center py-3 px-4">Occupancy</th>
                    <th className="text-center py-3 px-4">Capacity</th>
                    <th className="text-center py-3 px-4">%</th>
                  </tr>
                </thead>
                <tbody>
                  {shelters.map((s) => (
                    <tr key={s.id} className="border-b border-slate-800/50 hover:bg-white/5 transition-colors">
                      <td className="py-3 px-4 font-medium text-slate-200">{s.name}</td>
                      <td className="py-3 px-4 text-center text-slate-400 font-mono">{s.occupancy}</td>
                      <td className="py-3 px-4 text-center text-slate-400 font-mono">{s.capacity}</td>
                      <td className="py-3 px-4 text-center">
                        <StatusBadge severity={
                          (s.occupancy / s.capacity) > 0.8 ? 'critical' :
                          (s.occupancy / s.capacity) > 0.5 ? 'severe' : 'low'
                        } />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-slate-500 text-sm mt-4 font-mono">No shelters registered</p>
          )}
        </Card>

        <Card variant="glass" padding="md">
          <SectionHeader title="Active Disaster Zones" />
          {disasters && disasters.length > 0 ? (
            <div className="overflow-x-auto mt-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50 text-sm font-mono uppercase tracking-widest text-slate-400">
                    <th className="text-left py-3 px-4">Type</th>
                    <th className="text-left py-3 px-4">Severity</th>
                    <th className="text-center py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {disasters.map((d) => (
                    <tr key={d.id} className="border-b border-slate-800/50 hover:bg-white/5 transition-colors">
                      <td className="py-3 px-4 font-medium text-slate-200">{d.type}</td>
                      <td className="py-3 px-4 capitalize text-slate-400">{d.severity}</td>
                      <td className="py-3 px-4 text-center">
                        <StatusBadge severity={d.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-slate-500 text-sm mt-4 font-mono">No disaster zones</p>
          )}
        </Card>
      </div>
    </div>
  );
}