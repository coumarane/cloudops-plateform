import { Suspense } from "react";
import { AlertsConsole } from "@/components/alerts/AlertsConsole";

export const dynamic = "force-dynamic";

export default function AlertsPage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading alerts…</p>}>
      <AlertsConsole />
    </Suspense>
  );
}
