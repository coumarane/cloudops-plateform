import { Suspense } from "react";
import { AdministrationApp } from "@/components/admin/AdministrationApp";

export const dynamic = "force-dynamic";

export default function AdministrationPage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading administration…</p>}>
      <AdministrationApp />
    </Suspense>
  );
}
