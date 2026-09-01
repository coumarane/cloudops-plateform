import { isProductionEnvironment } from "@/lib/dashboard";
import type { Environment } from "@/lib/types";

export function EnvBadge({ environment }: { environment: Environment }) {
  const production = isProductionEnvironment(environment);

  return (
    <span
      className={
        production
          ? "rounded bg-prd px-1.5 py-0.5 text-[9px] font-bold text-white"
          : "rounded bg-surface-low px-1.5 py-0.5 text-[9px] font-bold text-ink"
      }
    >
      {environment}
    </span>
  );
}
