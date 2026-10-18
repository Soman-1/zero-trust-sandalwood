/** Display labels for the age / survival / host / heartwood / GPS decision. */

export const BIOMETRICS_FIELD_MEASURED = 'FIELD_MEASURED';
export const BIOMETRICS_ALLOMETRIC_ESTIMATE = 'ALLOMETRIC_ESTIMATE';

export function ageLabel(
  plantingYear?: number | null,
  estimatedAge?: number | null,
  biometricsSource?: string | null
): string {
  if (plantingYear) {
    const age = Math.max(0, new Date().getFullYear() - plantingYear);
    return `${age} yrs (planting record)`;
  }
  if (estimatedAge) {
    const years = Math.round(estimatedAge);
    if (biometricsSource === BIOMETRICS_ALLOMETRIC_ESTIMATE) {
      return `~${years} yrs (allometric estimate, no planting record)`;
    }
    return `~${years} yrs (estimated)`;
  }
  return 'Age unknown';
}

export function survivalLabel(eventDate?: string | null): string {
  if (eventDate && eventDate.trim()) {
    return `Last observed alive on ${eventDate.trim()}`;
  }
  return 'Observation date unknown — not confirmed alive today';
}

export function gpsLabel(gpsAccuracy?: number | null): string {
  if (gpsAccuracy == null || Number.isNaN(gpsAccuracy)) {
    return 'GPS uncertainty unknown';
  }
  return `±${Math.round(gpsAccuracy)} m`;
}

export function hostsLabel(hostNotes?: string | null): string {
  const text = (hostNotes || '').trim();
  return text || 'Hosts not surveyed — needs a field visit to record neighbouring species';
}

export function heartwoodEstimateLabel(kg?: number | null): string {
  if (kg == null || Number.isNaN(kg)) {
    return 'Heartwood unknown';
  }
  return `~${kg.toFixed(1)} kg (estimated, not a measured core)`;
}
