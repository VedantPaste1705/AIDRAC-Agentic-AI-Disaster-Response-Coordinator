const INCIDENT_ID_KEY = 'aidrac_incident_id';

export function getOrCreateIncidentId(): string {
  if (typeof window === 'undefined') {
    return crypto.randomUUID();
  }
  let incidentId = localStorage.getItem(INCIDENT_ID_KEY);
  if (!incidentId) {
    incidentId = crypto.randomUUID();
    localStorage.setItem(INCIDENT_ID_KEY, incidentId);
  }
  return incidentId;
}

export function clearIncidentId(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(INCIDENT_ID_KEY);
  }
}

export function setIncincidentId(id: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(INCIDENT_ID_KEY, id);
  }
}