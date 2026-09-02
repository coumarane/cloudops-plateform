import { assertNoSecretValues, isProductionEnvironment } from "./dashboard";
import type { RenewalStatus } from "./certificates";
import { getEnvironmentIdentity } from "./environment-data";
import type { Environment, Provider, Region } from "./types";

export type ManagedCertificate = {
  id: string;
  name: string;
  domain: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  cluster: string;
  namespace: string;
  issuer: string;
  expiresOn: string;
  daysRemaining: number;
  renewalStatus: RenewalStatus;
};

function scope(provider: Provider, region: Region, environment: Environment) {
  const identity = getEnvironmentIdentity(provider, region, environment);
  return {
    provider,
    region,
    environment,
    cluster: identity.clusterName,
  };
}

export const MANAGED_CERTIFICATES: ManagedCertificate[] = [
  {
    id: "cert-amer-prd-wildcard",
    name: "ingress-tls-wildcard",
    domain: "*.prd.amer.example.com",
    ...scope("AWS", "AMER", "PRD"),
    namespace: "ingress-prd",
    issuer: "Let's Encrypt",
    expiresOn: "2026-09-14",
    daysRemaining: 12,
    renewalStatus: "Expiring",
  },
  {
    id: "cert-amer-dev-platform",
    name: "platform-api-tls",
    domain: "platform.dev.amer.example.com",
    ...scope("AWS", "AMER", "DEV"),
    namespace: "dev",
    issuer: "Amazon",
    expiresOn: "2027-03-02",
    daysRemaining: 181,
    renewalStatus: "OK",
  },
  {
    id: "cert-amer-uat-app",
    name: "app-ingress-tls",
    domain: "uat.amer.example.com",
    ...scope("AWS", "AMER", "UAT"),
    namespace: "uat",
    issuer: "Let's Encrypt",
    expiresOn: "2026-11-20",
    daysRemaining: 79,
    renewalStatus: "OK",
  },
  {
    id: "cert-emea-uat-finance",
    name: "finance-tls",
    domain: "finance.uat.emea.example.com",
    ...scope("AWS", "EMEA", "UAT"),
    namespace: "finance-uat",
    issuer: "Let's Encrypt",
    expiresOn: "2026-12-01",
    daysRemaining: 90,
    renewalStatus: "OK",
  },
  {
    id: "cert-emea-npd-sync",
    name: "sync-tls",
    domain: "npd.emea.example.com",
    ...scope("AWS", "EMEA", "NPD"),
    namespace: "npd",
    issuer: "DigiCert",
    expiresOn: "2027-01-15",
    daysRemaining: 135,
    renewalStatus: "OK",
  },
  {
    id: "cert-apac-int-auth",
    name: "auth-tls",
    domain: "int.apac.example.com",
    ...scope("AWS", "APAC", "INT/TST"),
    namespace: "int-tst",
    issuer: "Let's Encrypt",
    expiresOn: "2026-10-18",
    daysRemaining: 46,
    renewalStatus: "OK",
  },
  {
    id: "cert-apac-prd-payments",
    name: "payments-edge-tls",
    domain: "payments.prd.apac.example.com",
    ...scope("AWS", "APAC", "PRD"),
    namespace: "payments-prd",
    issuer: "Amazon",
    expiresOn: "2027-02-08",
    daysRemaining: 159,
    renewalStatus: "OK",
  },
  {
    id: "cert-china-dev-ack",
    name: "ack-dev-tls",
    domain: "dev.china.example.com",
    ...scope("Alibaba", "China", "DEV"),
    namespace: "dev",
    issuer: "Alibaba Cloud SSL",
    expiresOn: "2026-11-05",
    daysRemaining: 64,
    renewalStatus: "OK",
  },
  {
    id: "cert-china-uat-gateway",
    name: "gateway-tls",
    domain: "uat.china.example.com",
    ...scope("Alibaba", "China", "UAT"),
    namespace: "uat",
    issuer: "Alibaba Cloud SSL",
    expiresOn: "2026-12-12",
    daysRemaining: 101,
    renewalStatus: "OK",
  },
  {
    id: "cert-china-prd-wildcard",
    name: "ack-prd-wildcard",
    domain: "*.prd.china.example.com",
    ...scope("Alibaba", "China", "PRD"),
    namespace: "ingress-prd",
    issuer: "DigiCert",
    expiresOn: "2026-10-28",
    daysRemaining: 56,
    renewalStatus: "Renewing",
  },
];

export function filterManagedCertificates(
  certificates: ManagedCertificate[],
  filters: {
    provider: Provider | "all";
    region: Region | "all";
    environment: Environment | "all";
  },
): ManagedCertificate[] {
  return certificates.filter((certificate) => {
    if (filters.provider !== "all" && certificate.provider !== filters.provider) return false;
    if (filters.region !== "all" && certificate.region !== filters.region) return false;
    if (filters.environment !== "all" && certificate.environment !== filters.environment) {
      return false;
    }
    return true;
  });
}

export function summarizeCertificates(certificates: ManagedCertificate[]) {
  return {
    inScope: certificates.length,
    expiring14d: certificates.filter(
      (certificate) => certificate.daysRemaining > 0 && certificate.daysRemaining <= 14,
    ).length,
    expired: certificates.filter((certificate) => certificate.renewalStatus === "Expired").length,
    autoRenewOk: certificates.filter((certificate) => certificate.renewalStatus === "OK").length,
    prd: certificates.filter((certificate) => certificate.environment === "PRD").length,
    production: certificates.filter((certificate) =>
      isProductionEnvironment(certificate.environment),
    ).length,
  };
}

export function managedCertificateStrings(certificate: ManagedCertificate): string[] {
  return [
    certificate.id,
    certificate.name,
    certificate.domain,
    certificate.provider,
    certificate.region,
    certificate.environment,
    certificate.cluster,
    certificate.namespace,
    certificate.issuer,
    certificate.expiresOn,
    String(certificate.daysRemaining),
    certificate.renewalStatus,
  ];
}

function assertCertificatesSafe(): void {
  for (const certificate of MANAGED_CERTIFICATES) {
    if ("privateKey" in certificate || "pem" in certificate || "key" in certificate) {
      throw new Error("Private keys must never be stored in certificate catalog data.");
    }
  }
  assertNoSecretValues(MANAGED_CERTIFICATES.flatMap(managedCertificateStrings));
}

assertCertificatesSafe();
