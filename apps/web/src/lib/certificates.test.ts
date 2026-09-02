import { describe, expect, it } from "vitest";
import { containsSecretValue } from "./dashboard";
import {
  filterManagedCertificates,
  managedCertificateStrings,
  MANAGED_CERTIFICATES,
  summarizeCertificates,
} from "./certificates-data";
import { certificatesHref, parseCertificatesFilters } from "./certificates";

describe("certificate monitoring", () => {
  it("never includes private keys or secret values", () => {
    for (const certificate of MANAGED_CERTIFICATES) {
      expect("privateKey" in certificate).toBe(false);
      expect("pem" in certificate).toBe(false);
      expect("key" in certificate).toBe(false);
      for (const value of managedCertificateStrings(certificate)) {
        expect(containsSecretValue(value)).toBe(false);
      }
    }
  });

  it("covers AWS AMER, EMEA, APAC, and Alibaba China", () => {
    const scopes = new Set(
      MANAGED_CERTIFICATES.map((certificate) => `${certificate.provider} ${certificate.region}`),
    );
    expect(scopes).toEqual(new Set(["AWS AMER", "AWS EMEA", "AWS APAC", "Alibaba China"]));
  });

  it("features the AWS AMER PRD wildcard expiring in 12 days", () => {
    const featured = MANAGED_CERTIFICATES.find(
      (certificate) => certificate.id === "cert-amer-prd-wildcard",
    );
    expect(featured?.name).toBe("ingress-tls-wildcard");
    expect(featured?.domain).toBe("*.prd.amer.example.com");
    expect(featured?.provider).toBe("AWS");
    expect(featured?.region).toBe("AMER");
    expect(featured?.environment).toBe("PRD");
    expect(featured?.cluster).toBe("us-east-1-prd-k8s");
    expect(featured?.namespace).toBe("ingress-prd");
    expect(featured?.issuer).toBe("Let's Encrypt");
    expect(featured?.expiresOn).toBe("2026-09-14");
    expect(featured?.daysRemaining).toBe(12);
    expect(featured?.renewalStatus).toBe("Expiring");
  });

  it("filters by provider, region, and environment", () => {
    const chinaPrd = filterManagedCertificates(MANAGED_CERTIFICATES, {
      provider: "Alibaba",
      region: "China",
      environment: "PRD",
    });
    expect(chinaPrd).toHaveLength(1);
    expect(chinaPrd[0]?.name).toBe("ack-prd-wildcard");
    expect(chinaPrd[0]?.renewalStatus).toBe("Renewing");
  });

  it("builds catalog URLs without embedding key material", () => {
    expect(
      certificatesHref({
        provider: "AWS",
        region: "AMER",
        environment: "PRD",
        certificate: "cert-amer-prd-wildcard",
      }),
    ).toBe(
      "/certificates?provider=aws&region=amer&environment=prd&certificate=cert-amer-prd-wildcard",
    );
    expect(parseCertificatesFilters({ provider: "aws", region: "emea", environment: "uat" })).toEqual(
      {
        provider: "AWS",
        region: "EMEA",
        environment: "UAT",
        certificate: null,
      },
    );
  });

  it("summarizes expiring and PRD certificates for the KPI strip", () => {
    const summary = summarizeCertificates(MANAGED_CERTIFICATES);
    expect(summary.inScope).toBe(10);
    expect(summary.expiring14d).toBe(1);
    expect(summary.expired).toBe(0);
    expect(summary.autoRenewOk).toBe(8);
    expect(summary.prd).toBe(3);
    expect(summary.production).toBeGreaterThan(summary.prd);
  });
});
