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
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { useResource } from "@/lib/api/use-resource";
import { isLiveCredential, parseSecretAction, parseSecretsFilters, type SecretAction } from "@/lib/secrets";
import { listSecretAccounts, summarizeSecrets, type ManagedSecret } from "@/lib/secrets-data";
import { ENVIRONMENTS } from "@/lib/types";

type Notice = { tone: "ok" | "prd"; text: string };

export function SecretsManagement({
  initial,
}: {
  initial: ReturnType<typeof parseSecretsFilters>;
}) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const provider = parseProvider(searchParams.get("provider") ?? "") ?? initial.provider ?? "all";
  const region = parseRegion(searchParams.get("region") ?? "") ?? initial.region ?? "all";
  const account = searchParams.get("account") || initial.account || "all";
  const environment = parseEnvironment(searchParams.get("environment") ?? "") ?? initial.environment ?? "all";
  const selectedId = searchParams.get("secret") || initial.secret;
  const selectedAction = parseSecretAction(searchParams.get("action")) ?? initial.action;
  const [refreshKey, setRefreshKey] = useState(0);

  const regions = regionsForProvider(provider === "all" ? "all" : provider);
  const accountsState = useResource(
    (signal) => cloudOpsApi.accounts({ provider, region, environment }, signal),
    [provider, region, environment],
  );
  const state = useResource(
    (signal) =>
      cloudOpsApi.secrets(
        {
          provider,
          region,
          account,
          environment,
        },
        signal,
      ),
    [provider, region, account, environment, refreshKey],
  );
  const secrets = state.status === "success" ? state.data.items : [];
  const accounts =
    accountsState.status === "success"
      ? Array.from(new Set(accountsState.data.items.map((item) => item.account))).sort()
      : listSecretAccounts(secrets);
  const summary = summarizeSecrets(secrets);
  const selected = secrets.find((secret) => secret.id === selectedId) ?? null;

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

  async function confirmAction(
    secret: ManagedSecret,
    action: Exclude<SecretAction, "history">,
    input: {
      secretValue?: string;
      confirmed: boolean;
      reason: string;
      changeTicket: string;
      rotationPolicyDays?: number;
    },
  ) {
    const prd = secret.environment === "PRD";
    const live = isLiveCredential(secret.id);
    const confirmation = {
      confirmed: input.confirmed,
      reason: input.reason,
      changeTicket: input.changeTicket,
    };
    if (action === "validate") {
      if (!live) {
        throw new ApiError("Catalog rows cannot be validated until they are registered as credentials.", 400);
      }
      await cloudOpsApi.validateCredential(secret.id);
    } else if (action === "update") {
      if (!live) {
        throw new ApiError("Catalog rows cannot be updated until they are registered as credentials.", 400);
      }
      await cloudOpsApi.updateCredential(secret.id, {
        rotationPolicyDays: input.rotationPolicyDays,
        ...confirmation,
      });
    } else if (live) {
      await cloudOpsApi.replaceCredential(secret.id, {
        secretValue: input.secretValue,
        ...confirmation,
      });
    } else {
      await cloudOpsApi.createCredential({
        name: secret.name,
        provider: secret.provider,
        region: secret.region,
        account: secret.account,
        environment: secret.environment,
        credentialType: secret.credentialType || "application",
        secretValue: input.secretValue,
        ...confirmation,
      });
    }
    setNotice({
      tone: prd ? "prd" : "ok",
      text: prd
        ? `${actionLabel(action)} requested in PRD for ${secret.name}. Secret values were not retrieved.`
        : `${actionLabel(action)} requested for ${secret.name}. Secret values were not retrieved.`,
    });
    setRefreshKey((value) => value + 1);
    closeAction();
  }

  return (
    <>
      <PageHeader
        title="Secrets Management"
        subtitle="Provider → Region → Account → Environment → Credential. Secret values are never displayed and cannot be retrieved."
        meta={state.status === "success" ? `Last synced: ${state.data.lastSynced}` : "Last synced: —"}
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
          <QueryState state={state} loadingLabel="Loading secrets…" emptyLabel="No secrets in the current hierarchy filter." isEmpty={(data) => data.items.length === 0}>
            {() => (
              <>
                <section aria-label="Secrets summary" className="grid grid-cols-2 gap-4 md:grid-cols-5">
                  <Kpi label="Secrets in scope" value={summary.inScope} />
                  <Kpi label="Rotation overdue" value={summary.overdue} tone={summary.overdue > 0 ? "warning" : undefined} />
                  <Kpi label="Due within 14d" value={summary.dueSoon} tone={summary.dueSoon > 0 ? "warning" : undefined} />
                  <Kpi label="Validation failures" value={summary.invalid} tone={summary.invalid > 0 ? "warning" : undefined} />
                  <Kpi label="PRD secrets" value={summary.prd} tone={summary.prd > 0 ? "prd" : undefined} />
                </section>
                <section className="rounded border border-outline bg-white">
                  <div className="border-b border-outline bg-surface-low px-4 py-3">
                    <h2 className="text-[15px] font-semibold text-ink">Secrets catalog</h2>
                    <p className="mt-1 text-xs text-muted">
                      Metadata, fingerprints, and rotation state only. Secret values are never displayed and cannot be retrieved.
                    </p>
                  </div>
                  <SecretsTable secrets={secrets} onAction={openAction} />
                </section>
              </>
            )}
          </QueryState>
          <p className="border-t border-outline pt-4 text-center font-mono text-xs text-muted">
            Secret values are never displayed in this console and cannot be retrieved after they are stored.
          </p>
        </div>
      </main>
      {selected && selectedAction ? (
        <SecretActionDialog
          secret={selected}
          action={selectedAction}
          onClose={closeAction}
          onConfirm={(input) => confirmAction(selected, selectedAction === "history" ? "update" : selectedAction, input)}
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
  if (action === "replace") return "Replace";
  return "Validate";
}
