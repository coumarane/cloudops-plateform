import Link from "next/link";
import {
  ENVIRONMENT_TAB_LABELS,
  ENVIRONMENT_TABS,
  environmentHref,
  type EnvironmentTab,
} from "@/lib/environment";
import type { EnvironmentIdentity } from "@/lib/environment-data";

export function EnvironmentTabs({
  identity,
  current,
}: {
  identity: EnvironmentIdentity;
  current: EnvironmentTab;
}) {
  return (
    <div className="sticky top-16 z-30 border-b border-outline bg-white px-6">
      <nav className="flex gap-6 overflow-x-auto" aria-label="Environment sections">
        {ENVIRONMENT_TABS.map((tab) => {
          const active = tab === current;
          return (
            <Link
              key={tab}
              href={environmentHref(identity.provider, identity.region, identity.environment, tab)}
              aria-current={active ? "page" : undefined}
              className={
                active
                  ? "shrink-0 border-b-2 border-action py-3 text-[11px] font-bold uppercase tracking-wide text-action"
                  : "shrink-0 border-b-2 border-transparent py-3 text-[11px] font-bold uppercase tracking-wide text-muted hover:text-ink"
              }
            >
              {ENVIRONMENT_TAB_LABELS[tab]}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
