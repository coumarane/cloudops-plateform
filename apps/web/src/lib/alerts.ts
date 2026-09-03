import type { Environment, Provider, Region } from "@/lib/types";

export type AlertStatus = "OPEN" | "ACKNOWLEDGED" | "SUPPRESSED" | "RESOLVED" | string;
export type AlertSeverityLevel = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;

export type ManagedAlert = {
  id: string;
  alertType: string;
  sourceType: string;
  sourceId: string;
  provider: Provider | string;
  region: Region | string;
  accountId?: string;
  environmentId?: string;
  environment: Environment | string;
  applicationId?: string;
  clusterId?: string;
  severity: AlertSeverityLevel;
  uiSeverity?: string;
  status: AlertStatus;
  title: string;
  summary: string;
  fingerprint: string;
  firstSeenAt?: string | null;
  lastSeenAt?: string | null;
  occurrenceCount: number;
  acknowledgedAt?: string | null;
  acknowledgedBy?: string;
  acknowledgedComment?: string;
  resolvedAt?: string | null;
  resolutionReason?: string;
  correlationId?: string;
  metadata?: Record<string, unknown>;
  objectName: string;
  age: string;
  href: string;
  related?: {
    incident?: { id: string; title: string; status: string } | null;
    certificate?: { id: string; domain: string; status: string } | null;
    pipeline?: { id: string; name: string } | null;
    pipelineRun?: { id: string; status: string } | null;
    deploymentId?: string;
  };
  timeline?: AlertTimelineEvent[];
  notifications?: NotificationDelivery[];
};

export type AlertTimelineEvent = {
  id: string;
  alertId: string;
  eventType: string;
  title: string;
  detail: string;
  actor: string;
  createdAt?: string | null;
};

export type NotificationDelivery = {
  id: string;
  alertId: string;
  destinationId: string;
  destinationName: string;
  providerType: string;
  notificationType: string;
  status: string;
  attempt: number;
  sentAt?: string | null;
  failedAt?: string | null;
  errorCategory?: string;
  externalMessageId?: string;
  detail?: string;
};

export type NotificationDestination = {
  id: string;
  name: string;
  providerType: string;
  configurationReference: string;
  hasSecret: boolean;
  config: Record<string, unknown>;
  enabled: boolean;
  description: string;
};

export type NotificationPolicy = {
  id: string;
  name: string;
  initialEnabled: boolean;
  repeatAfterSeconds: number;
  escalateAfterSeconds: number;
  recoveryEnabled: boolean;
  steps: Array<{ id: string; delaySeconds: number; destinationId: string; stepType: string; enabled: boolean }>;
};

export type AlertRoutingRule = {
  id: string;
  name: string;
  enabled: boolean;
  providerFilter: string;
  regionFilter: string;
  accountFilter: string;
  environmentFilter: string;
  applicationFilter: string;
  severityFilter: string;
  alertTypeFilter: string;
  destinationId: string;
  policyId: string;
};

export type MaintenanceWindow = {
  id: string;
  name: string;
  scope: string;
  provider: string;
  region: string;
  environment: string;
  application: string;
  startsAt?: string | null;
  endsAt?: string | null;
  reason: string;
  changeTicket: string;
  createdBy: string;
  enabled: boolean;
};

export type AlertListResponse = {
  items: ManagedAlert[];
  kpis: {
    critical: number;
    high: number;
    medium: number;
    acknowledged: number;
    suppressed: number;
    open: number;
    prdCritical: number;
  };
  lastSynced: string;
};

export function alertHref(id?: string | null): string {
  if (!id) return "/alerts";
  return `/alerts?selected=${encodeURIComponent(id)}`;
}

export function isPrdAlert(alert: { environment?: string }): boolean {
  return (alert.environment || "").toUpperCase() === "PRD";
}

export function minutesAgo(iso?: string | null): string {
  if (!iso) return "—";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "—";
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (minutes < 1) return "just now";
  if (minutes === 1) return "1 minute";
  if (minutes < 60) return `${minutes} minutes`;
  const hours = Math.round(minutes / 60);
  return hours === 1 ? "1 hour" : `${hours} hours`;
}
