import { describe, expect, it } from "vitest";
import { containsSecretValue } from "./dashboard";
import { certificatesHref, parseCertificatesFilters } from "./certificates";
import { filterManagedCertificates, summarizeCertificates, type ManagedCertificate } from "./certificates-data";

const SAMPLE: ManagedCertificate[] = [
  {
    id: "cert-amer-prd-wildcard",
    name: "ingress-tls-wildcard",
    domain: "*.prd.amer.example.com",
    provider: "AWS",
    region: "AMER",
    environment: "PRD",
    cluster: "us-east-1-prd-k8s",
    namespace: "ingress-prd",
    issuer: "Let's Encrypt",
    expiresOn: "2026-09-14",
    daysRemaining: 12,
    renewalStatus: "Expiring",
  },
  {
    id: "cert-china-prd-wildcard",
    name: "ack-prd-wildcard",
    domain: "*.prd.china.example.com",
    provider: "Alibaba",
    region: "China",
    environment: "PRD",
    cluster: "cn-hangzhou-prd-ack",
    namespace: "ingress-prd",
    issuer: "DigiCert",
    expiresOn: "2026-10-28",
    daysRemaining: 56,
    renewalStatus: "Renewing",
  },
];

describe("certificate monitoring", () => {
  it("never includes private keys or secret values", () => {
    for (const certificate of SAMPLE) {
      expect("privateKey" in certificate).toBe(false);
      expect(containsSecretValue(certificate.domain)).toBe(false);
    }
  });

  it("filters by provider, region, and environment", () => {
    const chinaPrd = filterManagedCertificates(SAMPLE, {
      provider: "Alibaba",
      region: "China",
      environment: "PRD",
    });
    expect(chinaPrd[0]?.name).toBe("ack-prd-wildcard");
  });

  it("builds catalog URLs without embedding key material", () => {
    expect(
      certificatesHref({
        provider: "AWS",
        region: "AMER",
        environment: "PRD",
        certificate: "cert-amer-prd-wildcard",
      }),
    ).toBe("/certificates?provider=aws&region=amer&environment=prd&certificate=cert-amer-prd-wildcard");
    expect(parseCertificatesFilters({ provider: "aws", region: "emea", environment: "uat" })).toEqual({
      provider: "AWS",
      region: "EMEA",
      environment: "UAT",
      certificate: null,
    });
  });

  it("summarizes expiring and PRD certificates for the KPI strip", () => {
    const summary = summarizeCertificates(SAMPLE);
    expect(summary.expiring14d).toBe(1);
    expect(summary.prd).toBe(2);
  });
});
