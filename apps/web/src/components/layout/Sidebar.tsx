"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  AppWindow,
  ClipboardList,
  GitBranch,
  HardDrive,
  HeartPulse,
  KeyRound,
  LayoutDashboard,
  Layers,
  Network,
  Rocket,
  Server,
  Settings,
  ShieldCheck,
  Terminal,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NAV_ITEMS, type NavItem } from "@/lib/navigation";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";

const ICONS: Record<NavItem["icon"], LucideIcon> = {
  overview: LayoutDashboard,
  infrastructure: Network,
  clusters: Server,
  environments: Layers,
  applications: AppWindow,
  secrets: KeyRound,
  certificates: ShieldCheck,
  storage: HardDrive,
  health: HeartPulse,
  deployments: Rocket,
  pipelines: Workflow,
  github: Terminal,
  jobs: GitBranch,
  alerts: AlertTriangle,
  audit: ClipboardList,
  administration: Settings,
};

function isNavActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const status = useResource((signal) => cloudOpsApi.platformStatus(signal), []);

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-60 flex-col bg-sidebar py-6 text-sm">
      <div className="mb-8 px-6">
        <p className="text-xl font-semibold tracking-tight text-white">CloudOps Platform</p>
        <p className="mt-1 text-xs text-slate-400">Enterprise Ops</p>
        {status.status === "success" && status.data.demoMode ? (
          <p className="mt-2 inline-flex rounded bg-warning px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-ink">
            DEMO DATA
          </p>
        ) : null}
        {status.status === "success" && !status.data.demoMode ? (
          <p className="sr-only" data-source={status.data.dataSource}>
            Data source {status.data.dataSource}
          </p>
        ) : null}
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-4" aria-label="Primary">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.icon];
          const active = isNavActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={
                active
                  ? "flex items-center gap-3 rounded px-3 py-2 bg-action text-white"
                  : "flex items-center gap-3 rounded px-3 py-2 text-slate-300 hover:bg-slate-800 hover:text-white"
              }
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-4 flex items-center gap-3 px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-600 text-[10px] font-semibold text-slate-200">
          <Activity className="h-4 w-4" aria-hidden />
        </div>
        <p className="truncate text-sm text-white">ops@cloudops.local</p>
      </div>
    </aside>
  );
}
