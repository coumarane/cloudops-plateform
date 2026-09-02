import { Suspense } from "react";
import { SecretsManagement } from "@/components/secrets/SecretsManagement";

export default function SecretsPage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading secrets…</p>}>
      <SecretsManagement />
    </Suspense>
  );
}
