import { isProductionEnvironment } from "./dashboard";
import type { CertificateRecord } from "./domain";
import type { Environment, Provider, Region } from "./types";

export type ManagedCertificate = CertificateRecord;

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
    production: certificates.filter((certificate) => isProductionEnvironment(certificate.environment)).length,
  };
}
