import { isProductionEnvironment } from "@/lib/dashboard";
import type { Environment } from "@/lib/types";

export function ProductionWarningBanner({ environment }: { environment: Environment | "all" }) {
  const prd = environment === "PRD";
  const production = environment !== "all" && isProductionEnvironment(environment);

  if (!production) {
    return null;
  }

  return (
    <div className="space-y-4">
      {prd ? (
        <div className="border-y-4 border-prd bg-prd px-4 py-1 text-center text-[11px] font-bold uppercase tracking-wide text-white">
          Production environment
        </div>
      ) : null}
      <div
        role="alert"
        className={
          prd
            ? "border border-prd bg-prd/10 px-4 py-3"
            : "border border-prd/40 bg-prd/5 px-4 py-3"
        }
      >
        <p className="text-[11px] font-bold uppercase tracking-wide text-prd">
          {prd ? "Production environment — PRD" : "Production environment"}
        </p>
        <p className="mt-1 text-sm text-ink">
          Changes to credentials in {prd ? "PRD" : environment} are high-risk. Update, Replace, and Validate
          require explicit confirmation, a reason, and credential:prod_update. Secret values are never displayed
          and cannot be retrieved.
        </p>
      </div>
    </div>
  );
}
