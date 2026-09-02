"use client";

import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ProductionWarningBanner } from "@/components/secrets/ProductionWarningBanner";
import { SecretActionDialog } from "@/components/secrets/SecretActionDialog";
import { SecretsTable } from "@/components/secrets/SecretsTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { regionsForProvider } from "@/lib/dashboard";
import {
  environmentToSlug,
  parseEnvironment,
  parseProvider,
  parseRegion,
  providerToSlug,
  regionToSlug,
} from "@/lib/environment";
import { LAST_SYNCED_LABEL } from "@/lib/mock-data";
import { parseSecretAction, type SecretAction } from "@/lib/secrets";
import {
  filterManagedSecrets,
  listSecretAccounts,
  MANAGED_SECRETS,
  summarizeSecrets,
  type ManagedSecret,
} from "@/lib/secrets-data";
import { ENVIRONMENTS, type Environment, type Provider, type Region } from "@/lib/types";

type Notice = { tone: "ok" | "prd"; text: string };

export function SecretsManagement() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const provider = parseProvider(searchParams.get("provider") ?? "") ?? "all";
  const region = parseRegion(searchParams.get("region") ?? "") ?? "all";
  const account = searchParams.get("account") || "all";
  const environment = parseEnvironment(searchParams.get("environment") ?? "") ?? "all";
  const selectedId = searchParams.get("secret");
  const selectedAction = parseSecretAction(searchParams.get("action"));

  const regions = regionsForProvider(provider === "all" ? "all" : provider);
  const accounts = listSecretAccounts().filter((item) =>
    accountScope(item, provider, region, environment),
  );
  const secrets = filterManagedSecrets(MANAGED_SECRETS, {
    provider: provider === "all" ? "all" : provider,
    region: region === "all" ? "all" : region,
    account: account === "all" ? "all" : account,
    environment: environment === "all" ? "all" : environment,
  });
  const summary = summarizeSecrets(secrets);
  const selected =
    secrets.find((secret) => secret.id === selectedId) ??
    MANAGED_SECRETS.find((secret) => secret.id === selectedId) ??
    null;

  const [notice, setNotice] = useState<Notice | null>(null);

  function setFilter(next: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(next)) {
      if (!value || value === "all") params.delete(key);
      else params.set(key, value);
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  function openAction(secret: ManagedSecret, action: SecretAction) {
    setNotice(null);
    setFilter({
      secret: secret.id,
      action,
      provider: providerToSlug(secret.provider),
      region: regionToSlug(secret.region),
      account: secret.account,
      environment: environmentToSlug(secret.environment),
    });
  }

  function closeAction() {
    setFilter({ secret: null, action: null });
  }

  function confirmAction(secret: ManagedSecret, action: Exclude<SecretAction, "history">) {
    const prd = secret.environment === "PRD";
    setNotice({
      tone: prd ? "prd" : "ok",
      text: prd
        ? `${actionLabel(action)} requested in PRD for ${secret.name}. Secret values were not retrieved.`
        : `${actionLabel(action)} requested for ${secret.name}. Secret values were not retrieved.`,
    });
    closeAction();
  }

  return (
    <>
      <PageHeader
        title="Secrets Management"
        subtitle="Provider → Region → Account → Environment. Secret values are never displayed."
        meta={`Last synced: ${LAST_SYNCED_LABEL}`}
      />
      <div className="flex flex-wrap items-center gap-4 border-b border-outline bg-canvas px-6 py-2 text-[11px] font-bold uppercase tracking-wide text-muted">
        <span>Hierarchy:</span>
        <label className="flex items-center gap-2">
          Provider:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={provider === "all" ? "all" : providerToSlug(provider)}
            onChange={(event) =>
              setFilter({
                provider: event.target.value,
                region: null,
                account: null,
              })
            }
          >
            <option value="all">All providers</option>
            <option value="aws">AWS</option>
            <option value="alibaba">Alibaba</option>
          </select>
        </label>
        <label className="flex items-center gap-2">
          Region:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={region === "all" ? "all" : regionToSlug(region)}
            onChange={(event) => setFilter({ region: event.target.value, account: null })}
          >
            <option value="all">All regions</option>
            {regions.map((item) => (
              <option key={item} value={regionToSlug(item)}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          Account:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={account}
            onChange={(event) => setFilter({ account: event.target.value })}
          >
            <option value="all">All accounts</option>
            {accounts.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          Environment:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={environment === "all" ? "all" : environmentToSlug(environment)}
            onChange={(event) => setFilter({ environment: event.target.value })}
          >
            <option value="all">All environments</option>
            {ENVIRONMENTS.map((item) => (
              <option key={item} value={environmentToSlug(item)}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <ProductionWarningBanner environment={environment === "all" ? "all" : environment} />
          {notice ? (
            <p
              className={
                notice.tone === "prd"
                  ? "rounded border border-prd bg-prd/10 px-4 py-3 text-sm text-ink"
                  : "rounded border border-outline bg-white px-4 py-3 text-sm text-ink"
              }
            >
              {notice.text}
            </p>
          ) : null}
          <section aria-label="Secrets summary" className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <Kpi label="Secrets in scope" value={summary.inScope} />
            <Kpi label="Rotation overdue" value={summary.overdue} tone={summary.overdue > 0 ? "warning" : undefined} />
            <Kpi label="Due within 14d" value={summary.dueSoon} tone={summary.dueSoon > 0 ? "warning" : undefined} />
            <Kpi label="Validation failures" value={0} />
            <Kpi label="PRD secrets" value={summary.prd} tone={summary.prd > 0 ? "prd" : undefined} />
          </section>
          <section className="rounded border border-outline bg-white">
            <div className="border-b border-outline bg-surface-low px-4 py-3">
              <h2 className="text-[15px] font-semibold text-ink">Secrets catalog</h2>
              <p className="mt-1 text-xs text-muted">
                Rotation state and due dates only. Secret values are never displayed.
              </p>
            </div>
            <SecretsTable secrets={secrets} onAction={openAction} />
          </section>
          <p className="border-t border-outline pt-4 text-center font-mono text-xs text-muted">
            Secret values are never displayed in this console.
          </p>
        </div>
      </main>
      {selected && selectedAction ? (
        <SecretActionDialog
          secret={selected}
          action={selectedAction}
          onClose={closeAction}
          onConfirm={confirmAction}
        />
      ) : null}
    </>
  );
}

function Kpi({ label, value, tone }: { label: string; value: number; tone?: "warning" | "prd" }) {
  const bar =
    tone === "prd" ? "border-l-4 border-l-prd" : tone === "warning" ? "border-l-4 border-l-warning" : "border-l-4 border-l-outline";
  const valueClass = tone === "prd" ? "text-prd" : tone === "warning" ? "text-warning" : "text-ink";
  return (
    <article className={`rounded border border-outline bg-white p-3 ${bar}`}>
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <p className={`text-lg font-semibold ${valueClass}`}>{value}</p>
    </article>
  );
}

function actionLabel(action: Exclude<SecretAction, "history">): string {
  if (action === "update") return "Update";
  if (action === "rotate") return "Rotate";
  return "Validate";
}

function accountScope(
  account: string,
  provider: Provider | "all",
  region: Region | "all",
  environment: Environment | "all",
): boolean {
  const secrets = filterManagedSecrets(MANAGED_SECRETS, {
    provider: provider === "all" ? "all" : provider,
    region: region === "all" ? "all" : region,
    account: "all",
    environment: environment === "all" ? "all" : environment,
  });
  return secrets.some((secret) => secret.account === account);
}
