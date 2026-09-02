import { Suspense } from "react";
import { CertificateMonitoring } from "@/components/certificates/CertificateMonitoring";
import { parseCertificatesFilters } from "@/lib/certificates";

export const dynamic = "force-dynamic";

export default async function CertificatesPage({
  searchParams,
}: {
  searchParams: Promise<{
    provider?: string;
    region?: string;
    environment?: string;
    certificate?: string;
  }>;
}) {
  const initial = parseCertificatesFilters(await searchParams);
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading certificates…</p>}>
      <CertificateMonitoring initial={initial} />
    </Suspense>
  );
}
