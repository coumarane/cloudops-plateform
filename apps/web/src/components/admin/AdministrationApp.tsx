"use client";

import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { NotificationsAdmin } from "@/components/admin/NotificationsAdmin";
import { CatalogPanel, Kpi, KpiGrid, StatusChip } from "@/components/catalog/CatalogChrome";
import { PageHeader } from "@/components/layout/PageHeader";
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import { ONBOARDING_STEPS, type ManagedAccount, type ManagedEnvironment, type ManagedProvider } from "@/lib/platform";

const SECTIONS = [
  "providers",
  "accounts",
  "environments",
  "credentials",
  "applications",
  "integrations",
  "jobs",
  "settings",
] as const;

type Section = (typeof SECTIONS)[number];

const LABELS: Record<Section, string> = {
  providers: "Providers",
  accounts: "Cloud Accounts",
  environments: "Environments",
  credentials: "Credentials",
  applications: "Applications",
  integrations: "Integrations",
  jobs: "Discovery Jobs",
  settings: "Platform Settings",
};

export function AdministrationApp() {
  const search = useSearchParams();
  const initial = (SECTIONS as readonly string[]).includes(search.get("section") || "")
    ? (search.get("section") as Section)
    : "providers";
  const [section, setSection] = useState<Section>(initial);
  const [notice, setNotice] = useState("");
  const [nonce, setNonce] = useState(0);
  const status = useResource((signal) => cloudOpsApi.platformStatus(signal), [nonce]);

  function refresh(message?: string) {
    if (message) setNotice(message);
    setNonce((value) => value + 1);
  }

  return (
    <>
      <PageHeader title="Administration" subtitle="Configure providers, accounts, environments, and credentials. Secret values are never displayed." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          {notice ? <p className="rounded border border-outline bg-white px-4 py-2 text-sm text-ink">{notice}</p> : null}
          <QueryState state={status} loadingLabel="Loading platform status…">
            {(data) =>
              data.onboarding ? (
                <OnboardingCard onStart={() => setSection("providers")} />
              ) : (
                <p className="text-xs text-muted">
                  Data source {data.dataSource}
                  {data.bootstrapAdmin ? " · Bootstrap admin enabled" : ""}
                </p>
              )
            }
          </QueryState>
          <div className="flex flex-wrap gap-2">
            {SECTIONS.map((item) => (
              <button
                key={item}
                type="button"
                className={section === item ? "rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" : "rounded border border-outline px-3 py-1.5 text-xs font-semibold"}
                onClick={() => setSection(item)}
              >
                {LABELS[item]}
              </button>
            ))}
          </div>
          {section === "providers" ? <ProvidersPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "accounts" ? <AccountsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "environments" ? <EnvironmentsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "credentials" ? <CredentialsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "applications" ? <ApplicationsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "integrations" ? <IntegrationsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "jobs" ? <JobsPanel nonce={nonce} /> : null}
          {section === "settings" ? <SettingsPanel nonce={nonce} onNotice={refresh} /> : null}
        </div>
      </main>
    </>
  );
}

function OnboardingCard({ onStart }: { onStart: () => void }) {
  return (
    <section className="rounded border border-outline bg-white p-6">
      <h2 className="text-lg font-semibold text-ink">Welcome to CloudOps Platform</h2>
      <p className="mt-2 text-sm text-muted">No cloud providers are configured. Mock infrastructure is disabled.</p>
      <ol className="mt-4 list-decimal space-y-1 pl-5 text-sm text-ink">
        {ONBOARDING_STEPS.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <button type="button" className="mt-4 rounded bg-action px-4 py-2 text-sm font-semibold text-white" onClick={onStart}>
        Start Setup
      </button>
    </section>
  );
}

function ProvidersPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.managedProviders(signal), [nonce]);
  const [wizard, setWizard] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  if (selected) {
    return <ProviderDetails id={selected} onBack={() => setSelected(null)} onNotice={onNotice} />;
  }
  if (wizard) {
    return <ProviderWizard onDone={(message) => { setWizard(false); onNotice(message); }} onCancel={() => setWizard(false)} />;
  }
  return (
    <QueryState
      state={state}
      loadingLabel="Loading providers…"
    >
      {(data) => (
        <>
          {data.items.length === 0 ? null : (
            <KpiGrid>
              <Kpi label="Providers" value={data.items.length} />
              <Kpi label="Enabled" value={data.items.filter((item) => item.enabled).length} />
            </KpiGrid>
          )}
          <CatalogPanel title="Providers" hint="Logical CloudOps configuration. Credentials stay in SecretBackend.">
            <div className="border-b border-outline p-3">
              <button type="button" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" onClick={() => setWizard(true)}>
                Add Provider
              </button>
            </div>
            {data.items.length === 0 ? (
              <EmptyAction label="No cloud providers configured." action="Add Provider" onClick={() => setWizard(true)} />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Provider</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Accounts</th>
                    <th className="p-3">Environments</th>
                    <th className="p-3">Last validated</th>
                    <th className="p-3">Last synchronized</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row: ManagedProvider) => (
                    <tr key={row.id} className="border-b border-outline">
                      <td className="p-3">
                        <button type="button" className="font-semibold text-action hover:underline" onClick={() => setSelected(row.id)}>
                          {row.name}
                        </button>
                      </td>
                      <td className="p-3 text-muted">{row.providerType}</td>
                      <td className="p-3"><StatusChip value={row.status} /></td>
                      <td className="p-3">{row.accounts}</td>
                      <td className="p-3">{row.environments}</td>
                      <td className="p-3 font-mono text-xs text-muted">{row.lastValidatedAt || "—"}</td>
                      <td className="p-3 font-mono text-xs text-muted">{row.lastSynchronizedAt || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CatalogPanel>
        </>
      )}
    </QueryState>
  );
}

function ProviderWizard({ onDone, onCancel }: { onDone: (message: string) => void; onCancel: () => void }) {
  const types = useResource((signal) => cloudOpsApi.providerTypes(signal), []);
  const [step, setStep] = useState(1);
  const [providerType, setProviderType] = useState("AWS");
  const [name, setName] = useState("AWS Corporate");
  const [description, setDescription] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [authStrategy, setAuthStrategy] = useState("AssumeRole");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const strategies = providerType === "Alibaba" ? ["RAM", "STS", "AccessKey"] : ["AssumeRole", "IAM"];

  async function save() {
    setBusy(true);
    setError("");
    try {
      const created = await cloudOpsApi.createProvider({ providerType, name, description, enabled, authStrategy });
      onDone(`Provider ${created.name} saved`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <CatalogPanel title="Add Provider" hint="Do not store plaintext credentials on the provider.">
      <div className="space-y-4 p-4">
        <p className="text-xs text-muted">Step {step} of 5</p>
        {step === 1 ? (
          <div className="flex gap-2">
            {(types.status === "success" ? types.data.items : [{ id: "AWS", name: "AWS" }, { id: "Alibaba", name: "Alibaba Cloud" }]).map((item) => (
              <button key={item.id} type="button" className={providerType === item.id ? "rounded bg-action px-3 py-2 text-sm text-white" : "rounded border border-outline px-3 py-2 text-sm"} onClick={() => { setProviderType(item.id); setName(item.id === "AWS" ? "AWS Corporate" : "Alibaba China"); setAuthStrategy(item.id === "AWS" ? "AssumeRole" : "RAM"); }}>
                {item.name}
              </button>
            ))}
          </div>
        ) : null}
        {step === 2 ? (
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Name" value={name} onChange={setName} />
            <Field label="Description" value={description} onChange={setDescription} />
            <label className="text-sm"><input type="checkbox" className="mr-2" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />Enabled</label>
          </div>
        ) : null}
        {step === 3 ? (
          <div className="flex flex-wrap gap-2">
            {strategies.map((item) => (
              <button key={item} type="button" className={authStrategy === item ? "rounded bg-action px-3 py-2 text-sm text-white" : "rounded border border-outline px-3 py-2 text-sm"} onClick={() => setAuthStrategy(item)}>
                {item}
              </button>
            ))}
            <p className="w-full text-xs text-muted">Use a credential reference on the account. Role ARN / RAM role are metadata only.</p>
          </div>
        ) : null}
        {step === 4 ? <p className="text-sm">Validation runs after an account is attached. Save the provider first, then add an account and click Validate.</p> : null}
        {step === 5 ? <p className="text-sm">Ready to save {name} ({providerType}, {authStrategy}).</p> : null}
        {error ? <p className="text-sm text-critical">{error}</p> : null}
        <div className="flex gap-2">
          <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={onCancel}>Cancel</button>
          {step > 1 ? <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={() => setStep(step - 1)}>Back</button> : null}
          {step < 5 ? <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" onClick={() => setStep(step + 1)}>Next</button> : (
            <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" disabled={busy} onClick={() => void save()}>{busy ? "Saving…" : "Save"}</button>
          )}
        </div>
      </div>
    </CatalogPanel>
  );
}

function ProviderDetails({ id, onBack, onNotice }: { id: string; onBack: () => void; onNotice: (message: string) => void }) {
  const [nonce, setNonce] = useState(0);
  const state = useResource((signal) => cloudOpsApi.managedProvider(id, signal), [id, nonce]);
  const [busy, setBusy] = useState("");
  async function run(action: "validate" | "discover" | "disable" | "enable") {
    setBusy(action);
    try {
      if (action === "validate") {
        const result = await cloudOpsApi.validateProvider(id);
        onNotice(result.connected ? `Connection validation succeeded · Account ${result.account} · Principal ${result.principal}` : `Validation failed: ${result.detail}`);
      } else if (action === "discover") {
        const result = await cloudOpsApi.discoverProvider(id);
        onNotice(`Cluster discovery started. Job ${result.jobId}`);
      } else {
        await cloudOpsApi.updateProvider(id, { enabled: action === "enable" });
        onNotice(`Provider ${action}d`);
      }
      setNonce((value) => value + 1);
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Action failed");
    } finally {
      setBusy("");
    }
  }
  return (
    <QueryState state={state} loadingLabel="Loading provider…">
      {(row) => (
        <div className="space-y-4">
          <button type="button" className="text-sm text-action" onClick={onBack}>← Providers</button>
          <CatalogPanel title={row.name} hint={`${row.providerType} · ${row.authStrategy}`}>
            <div className="grid grid-cols-2 gap-4 p-4 md:grid-cols-5">
              <Meta label="Accounts" value={String(row.accounts)} />
              <Meta label="Environments" value={String(row.environments)} />
              <Meta label="Clusters" value={String(row.clusters)} />
              <Meta label="Last validation" value={row.validationStatus || "—"} />
              <Meta label="Last discovery" value={row.lastSynchronizedAt || "—"} />
            </div>
            <div className="flex flex-wrap gap-2 border-t border-outline p-4">
              <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" disabled={!!busy} onClick={() => void run("validate")}>{busy === "validate" ? "Validating…" : "Validate Provider"}</button>
              <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" disabled={!!busy} onClick={() => void run("discover")}>{busy === "discover" ? "Starting…" : "Discover All"}</button>
              <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={() => void run(row.enabled ? "disable" : "enable")}>{row.enabled ? "Disable" : "Enable"}</button>
            </div>
          </CatalogPanel>
          <div className="grid gap-4 md:grid-cols-2">
            <CatalogPanel title="Accounts">
              <ul className="p-4 text-sm">{(row.accountsDetail || []).map((item) => <li key={item.id}>{item.name} · {item.readiness}</li>)}</ul>
            </CatalogPanel>
            <CatalogPanel title="Environments">
              <ul className="p-4 text-sm">{(row.environmentsDetail || []).map((item) => <li key={item.id}>{item.name} · {item.readiness}</li>)}</ul>
            </CatalogPanel>
          </div>
        </div>
      )}
    </QueryState>
  );
}

function AccountsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const providers = useResource((signal) => cloudOpsApi.managedProviders(signal), [nonce]);
  const accounts = useResource((signal) => cloudOpsApi.managedAccounts(signal), [nonce]);
  const [form, setForm] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  if (selected) return <AccountDetails id={selected} onBack={() => setSelected(null)} onNotice={onNotice} />;
  return (
    <>
      {form && providers.status === "success" ? (
        <AccountForm providers={providers.data.items} onDone={(message) => { setForm(false); onNotice(message); }} onCancel={() => setForm(false)} />
      ) : null}
      <QueryState state={accounts} loadingLabel="Loading accounts…">
        {(data) => (
          <CatalogPanel title="Cloud Accounts" hint="NONPROD / PROD class. Secrets stay in SecretBackend.">
            <div className="border-b border-outline p-3">
              <button type="button" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" onClick={() => setForm(true)}>Add Account</button>
            </div>
            {data.items.length === 0 ? (
              <EmptyAction label="No cloud accounts configured." action="Add Account" onClick={() => setForm(true)} />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Account</th><th className="p-3">Provider</th><th className="p-3">Region</th><th className="p-3">Class</th><th className="p-3">Readiness</th><th className="p-3">Clusters</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row: ManagedAccount) => (
                    <tr key={row.id} className="border-b border-outline">
                      <td className="p-3"><button type="button" className="font-semibold text-action" onClick={() => setSelected(row.id)}>{row.name}</button></td>
                      <td className="p-3">{row.provider}</td>
                      <td className="p-3">{row.region}</td>
                      <td className="p-3">{row.accountClassCode || row.accountClass}</td>
                      <td className="p-3"><StatusChip value={row.readiness} /></td>
                      <td className="p-3">{row.clusters}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CatalogPanel>
        )}
      </QueryState>
    </>
  );
}

function AccountForm({ providers, onDone, onCancel }: { providers: ManagedProvider[]; onDone: (message: string) => void; onCancel: () => void }) {
  const first = providers[0];
  const [providerId, setProviderId] = useState(first?.id || "");
  const selected = providers.find((item) => item.id === providerId);
  const alibaba = selected?.providerType === "Alibaba";
  const [name, setName] = useState(alibaba ? "Alibaba China NonProd" : "AWS EMEA NonProd");
  const [accountId, setAccountId] = useState("");
  const [region, setRegion] = useState(alibaba ? "China" : "EMEA");
  const [cloudRegion, setCloudRegion] = useState(alibaba ? "cn-hangzhou" : "eu-west-1");
  const [roleArn, setRoleArn] = useState("");
  const [accountClass, setAccountClass] = useState("NONPROD");
  const [credentialRef, setCredentialRef] = useState("");
  const [secretValue, setSecretValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    setBusy(true);
    setError("");
    try {
      let ref = credentialRef;
      if (secretValue) {
        const credential = await cloudOpsApi.createCredential({
          name: `${name}-identity`,
          provider: alibaba ? "alibaba" : "aws",
          region: region.toLowerCase(),
          account: name.toLowerCase().replace(/\s+/g, "-"),
          environment: accountClass === "PROD" ? "prd" : "dev",
          credentialType: alibaba ? "ram_role" : "sts_assume_role",
          secretValue,
          roleArn,
        });
        ref = credential.secretReference || credential.id;
      }
      await cloudOpsApi.createAccount({
        providerId,
        name,
        accountId,
        region,
        cloudRegion,
        cloudRegions: [cloudRegion],
        roleArn: alibaba ? undefined : roleArn,
        ramRole: alibaba ? roleArn : undefined,
        accountClass,
        credentialRef: ref,
        authStrategy: selected?.authStrategy,
      });
      onDone(`Account ${name} saved`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <CatalogPanel title="Add Account" hint="Access keys and webhook URLs are write-only.">
      <div className="grid gap-3 p-4 md:grid-cols-2">
        <label className="text-sm">Provider
          <select className="mt-1 w-full rounded border border-outline p-2" value={providerId} onChange={(event) => setProviderId(event.target.value)}>
            {providers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <Field label="Account name" value={name} onChange={setName} />
        <Field label={alibaba ? "Alibaba account ID" : "AWS account ID"} value={accountId} onChange={setAccountId} />
        <Field label="Logical region" value={region} onChange={setRegion} />
        <Field label="Cloud region" value={cloudRegion} onChange={setCloudRegion} />
        <Field label={alibaba ? "RAM role" : "Role ARN"} value={roleArn} onChange={setRoleArn} />
        <label className="text-sm">Account class
          <select className="mt-1 w-full rounded border border-outline p-2" value={accountClass} onChange={(event) => setAccountClass(event.target.value)}>
            <option value="NONPROD">NONPROD</option>
            <option value="PROD">PROD</option>
          </select>
        </label>
        <Field label="Existing credential reference" value={credentialRef} onChange={setCredentialRef} />
        <label className="text-sm md:col-span-2">New secret material (write-only)
          <input type="password" autoComplete="new-password" className="mt-1 w-full rounded border border-outline p-2" value={secretValue} onChange={(event) => setSecretValue(event.target.value)} />
        </label>
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
        <div className="flex gap-2 md:col-span-2">
          <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={onCancel}>Cancel</button>
          <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" disabled={busy || !providerId} onClick={() => void save()}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </div>
    </CatalogPanel>
  );
}

function AccountDetails({ id, onBack, onNotice }: { id: string; onBack: () => void; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.managedAccount(id, signal), [id]);
  const [busy, setBusy] = useState("");
  async function run(action: "validate" | "discover") {
    setBusy(action);
    try {
      if (action === "validate") {
        const result = await cloudOpsApi.validateAccount(id);
        onNotice(result.connected ? `Connection validation succeeded · Account ${result.account} · Principal ${result.principal}` : `Validation failed: ${result.detail}`);
      } else {
        const result = await cloudOpsApi.discoverAccount(id);
        onNotice(`Cluster discovery started. Job ${result.jobId}`);
      }
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Action failed");
    } finally {
      setBusy("");
    }
  }
  return (
    <QueryState state={state} loadingLabel="Loading account…">
      {(row) => (
        <div className="space-y-4">
          <button type="button" className="text-sm text-action" onClick={onBack}>← Accounts</button>
          <CatalogPanel title={row.name} hint={`${row.provider} · ${row.authStrategy || "AssumeRole"}`}>
            <div className="grid grid-cols-2 gap-4 p-4 md:grid-cols-4">
              <Meta label="Account ID" value={row.accountId || "—"} />
              <Meta label="Role" value={row.roleArn || row.ramRole || "—"} />
              <Meta label="Environments" value={(row.hostedEnvironments || []).join(" ") || "—"} />
              <Meta label="Last validation" value={row.validationStatus || "—"} />
            </div>
            <div className="flex gap-2 border-t border-outline p-4">
              <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" disabled={!!busy} onClick={() => void run("validate")}>{busy === "validate" ? "Validating…" : "Validate"}</button>
              <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" disabled={!!busy} onClick={() => void run("discover")}>{busy === "discover" ? "Starting…" : "Discover"}</button>
              <button
                type="button"
                className="rounded border border-outline px-3 py-1.5 text-xs"
                onClick={() => {
                  if (window.confirm(`Delete ${row.name} if unused?`)) {
                    void cloudOpsApi.deleteAccount(id).then(() => { onNotice(`Account ${row.name} deleted`); onBack(); }).catch((error) => onNotice(error instanceof Error ? error.message : "Delete failed"));
                  }
                }}
              >
                Delete if unused
              </button>
            </div>
          </CatalogPanel>
        </div>
      )}
    </QueryState>
  );
}

function EnvironmentsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const accounts = useResource((signal) => cloudOpsApi.managedAccounts(signal), [nonce]);
  const envs = useResource((signal) => cloudOpsApi.managedEnvironments(signal), [nonce]);
  const [form, setForm] = useState(false);
  return (
    <>
      {form && accounts.status === "success" ? (
        <EnvironmentForm accounts={accounts.data.items} onDone={(message) => { setForm(false); onNotice(message); }} onCancel={() => setForm(false)} />
      ) : null}
      <QueryState state={envs} loadingLabel="Loading environments…">
        {(data) => (
          <CatalogPanel title="Environments" hint="Environment class is configurable. PRD is visually distinct.">
            <div className="border-b border-outline p-3">
              <button type="button" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" onClick={() => setForm(true)}>Add Environment</button>
            </div>
            {data.items.length === 0 ? (
              <EmptyAction label="No environments configured." action="Add Environment" onClick={() => setForm(true)} />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Name</th><th className="p-3">Class</th><th className="p-3">Provider</th><th className="p-3">Region</th><th className="p-3">Account</th><th className="p-3">Readiness</th><th className="p-3" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row: ManagedEnvironment) => (
                    <tr key={row.id} className={row.environment === "PRD" ? "border-b border-prd/30 bg-prd/5" : "border-b border-outline"}>
                      <td className="p-3 font-semibold">{row.name}</td>
                      <td className="p-3">{row.environment}</td>
                      <td className="p-3">{row.provider}</td>
                      <td className="p-3">{row.region}</td>
                      <td className="p-3 font-mono text-xs">{row.account}</td>
                      <td className="p-3"><StatusChip value={row.readiness} /></td>
                      <td className="p-3">
                        <button type="button" className="mr-2 text-xs font-semibold text-action" onClick={() => void cloudOpsApi.discoverEnvironment(row.id).then((result) => onNotice(`Cluster discovery started. Job ${result.jobId}`))}>Discover Clusters</button>
                        <button type="button" className="text-xs text-muted" onClick={() => void cloudOpsApi.updateEnvironment(row.id, { enabled: !row.enabled }).then(() => onNotice(`Environment ${row.enabled ? "disabled" : "enabled"}`))}>{row.enabled ? "Disable" : "Enable"}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CatalogPanel>
        )}
      </QueryState>
    </>
  );
}

function EnvironmentForm({ accounts, onDone, onCancel }: { accounts: ManagedAccount[]; onDone: (message: string) => void; onCancel: () => void }) {
  const [accountId, setAccountId] = useState(accounts[0]?.id || "");
  const [name, setName] = useState("DEV");
  const [environmentClass, setEnvironmentClass] = useState("DEV");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      await cloudOpsApi.createEnvironment({ accountId, name, environmentClass, code: environmentClass, description });
      onDone(`Environment ${environmentClass} saved`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <CatalogPanel title="Add Environment">
      <div className="grid gap-3 p-4 md:grid-cols-2">
        <label className="text-sm">Cloud account
          <select className="mt-1 w-full rounded border border-outline p-2" value={accountId} onChange={(event) => setAccountId(event.target.value)}>
            {accounts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label className="text-sm">Environment class
          <select className="mt-1 w-full rounded border border-outline p-2" value={environmentClass} onChange={(event) => { setEnvironmentClass(event.target.value); setName(event.target.value); }}>
            {["DEV", "INT/TST", "UAT", "NPD", "PRD"].map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <Field label="Name" value={name} onChange={setName} />
        <Field label="Description" value={description} onChange={setDescription} />
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
        <div className="flex gap-2 md:col-span-2">
          <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={onCancel}>Cancel</button>
          <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" disabled={busy || !accountId} onClick={() => void save()}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </div>
    </CatalogPanel>
  );
}

function CredentialsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.credentials({}, signal), [nonce]);
  const [form, setForm] = useState(false);
  const [historyId, setHistoryId] = useState<string | null>(null);
  const history = useResource((signal) => (historyId ? cloudOpsApi.credentialHistory(historyId, signal) : Promise.resolve(null)), [historyId]);
  return (
    <>
      {form ? <CredentialForm onDone={(message) => { setForm(false); onNotice(message); }} onCancel={() => setForm(false)} /> : null}
      <QueryState state={state} loadingLabel="Loading credentials…">
        {(data) => (
          <CatalogPanel title="Credentials" hint="Write-only secret material. Existing values are never shown.">
            <div className="border-b border-outline p-3">
              <button type="button" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" onClick={() => setForm(true)}>Add Credential</button>
            </div>
            {data.items.length === 0 ? (
              <EmptyAction label="No credentials configured." action="Add Credential" onClick={() => setForm(true)} />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Name</th><th className="p-3">Type</th><th className="p-3">Scope</th><th className="p-3">Status</th><th className="p-3" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <tr key={row.id} className="border-b border-outline">
                      <td className="p-3 font-semibold">{row.name}</td>
                      <td className="p-3">{row.credentialType}</td>
                      <td className="p-3 font-mono text-xs">{row.provider} / {row.region} / {row.environment}</td>
                      <td className="p-3"><StatusChip value={row.status} /></td>
                      <td className="p-3 space-x-2">
                        <button type="button" className="text-xs text-action" onClick={() => void cloudOpsApi.validateCredential(row.id).then((result) => onNotice(`Credential validation queued. Job ${result.jobId}`))}>Validate</button>
                        <button type="button" className="text-xs text-action" onClick={() => setHistoryId(row.id)}>History</button>
                        <button type="button" className="text-xs text-muted" onClick={() => void cloudOpsApi.updateCredential(row.id, { status: "DISABLED" }).then(() => onNotice(`Credential ${row.name} disabled`))}>Disable</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {historyId && history.status === "success" && history.data ? (
              <div className="border-t border-outline p-4 text-sm">
                <p className="font-semibold">History</p>
                <ul className="mt-2 space-y-1 text-xs text-muted">
                  {history.data.items.map((item) => (
                    <li key={item.id}>{item.createdAt} · {item.action} · {item.result} · {item.detail}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CatalogPanel>
        )}
      </QueryState>
    </>
  );
}

function CredentialForm({ onDone, onCancel }: { onDone: (message: string) => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("AWS");
  const [region, setRegion] = useState("EMEA");
  const [account, setAccount] = useState("");
  const [environment, setEnvironment] = useState("DEV");
  const [credentialType, setCredentialType] = useState("sts_assume_role");
  const [roleArn, setRoleArn] = useState("");
  const [secretValue, setSecretValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      await cloudOpsApi.createCredential({
        name,
        provider: provider.toLowerCase(),
        region: region.toLowerCase(),
        account: account || name.toLowerCase().replace(/\s+/g, "-"),
        environment: environment === "INT/TST" ? "int-tst" : environment.toLowerCase(),
        credentialType,
        roleArn,
        secretValue: secretValue || undefined,
      });
      onDone(`Credential ${name} saved`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <CatalogPanel title="Add Credential" hint="Secret material is write-only and stored in SecretBackend.">
      <div className="grid gap-3 p-4 md:grid-cols-2">
        <Field label="Name" value={name} onChange={setName} />
        <label className="text-sm">Provider
          <select className="mt-1 w-full rounded border border-outline p-2" value={provider} onChange={(event) => setProvider(event.target.value)}>
            <option>AWS</option>
            <option>Alibaba</option>
          </select>
        </label>
        <Field label="Region" value={region} onChange={setRegion} />
        <Field label="Account alias" value={account} onChange={setAccount} />
        <label className="text-sm">Environment
          <select className="mt-1 w-full rounded border border-outline p-2" value={environment} onChange={(event) => setEnvironment(event.target.value)}>
            {["DEV", "INT/TST", "UAT", "NPD", "PRD"].map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
        <label className="text-sm">Type
          <select className="mt-1 w-full rounded border border-outline p-2" value={credentialType} onChange={(event) => setCredentialType(event.target.value)}>
            <option value="sts_assume_role">STS AssumeRole</option>
            <option value="iam_role">IAM role</option>
            <option value="ram_role">RAM role</option>
            <option value="access_key">Access key</option>
          </select>
        </label>
        <Field label="Role ARN / RAM role" value={roleArn} onChange={setRoleArn} />
        <label className="text-sm md:col-span-2">Secret material (write-only)
          <input type="password" autoComplete="new-password" className="mt-1 w-full rounded border border-outline p-2" value={secretValue} onChange={(event) => setSecretValue(event.target.value)} />
        </label>
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
        <div className="flex gap-2 md:col-span-2">
          <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={onCancel}>Cancel</button>
          <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" disabled={busy || !name} onClick={() => void save()}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </div>
    </CatalogPanel>
  );
}

function IntegrationsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.adminIntegrations(signal), [nonce]);
  const [github, setGithub] = useState(false);
  const [azure, setAzure] = useState(false);
  return (
    <div className="space-y-6">
      {github ? <GithubForm onDone={(message) => { setGithub(false); onNotice(message); }} onCancel={() => setGithub(false)} /> : null}
      {azure ? <AzureForm onDone={(message) => { setAzure(false); onNotice(message); }} onCancel={() => setAzure(false)} /> : null}
      <QueryState state={state} loadingLabel="Loading integrations…">
        {(data) => (
          <CatalogPanel title="Integrations" hint="GitHub, Azure DevOps, and notification destinations. Tokens stay in SecretBackend.">
            <div className="flex gap-2 border-b border-outline p-3">
              <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" onClick={() => setGithub(true)}>Add GitHub App</button>
              <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={() => setAzure(true)}>Add Azure DevOps</button>
            </div>
            {data.items.length === 0 ? <p className="p-4 text-sm text-muted">No integrations configured.</p> : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Integration</th><th className="p-3">Type</th><th className="p-3">Status</th><th className="p-3">Scope</th><th className="p-3" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <tr key={row.id} className="border-b border-outline">
                      <td className="p-3 font-semibold">{row.name}</td>
                      <td className="p-3">{row.type || ""}</td>
                      <td className="p-3"><StatusChip value={row.status} /></td>
                      <td className="p-3">{row.scope}</td>
                      <td className="p-3 space-x-2">
                        {row.type === "github" ? (
                          <>
                            <button type="button" className="text-xs text-action" onClick={() => void cloudOpsApi.validateGithubIntegration(row.id).then((result) => onNotice(result.connected ? "GitHub validation succeeded" : result.detail))}>Validate</button>
                            <button type="button" className="text-xs text-action" onClick={() => void cloudOpsApi.triggerGithubSync().then(() => onNotice("GitHub synchronize started"))}>Synchronize</button>
                            <button type="button" className="text-xs text-muted" onClick={() => void cloudOpsApi.updateGithubIntegration(row.id, { enabled: false }).then(() => onNotice("GitHub integration disabled"))}>Disable</button>
                          </>
                        ) : null}
                        {row.type === "azure_devops" ? (
                          <>
                            <button type="button" className="text-xs text-action" onClick={() => void cloudOpsApi.validateAzureDevOpsIntegration(row.id).then((result) => onNotice(result.connected ? "Azure DevOps validation succeeded" : result.detail))}>Validate</button>
                            <button type="button" className="text-xs text-action" onClick={() => void cloudOpsApi.triggerPipelineSync().then(() => onNotice("Pipeline synchronize started"))}>Synchronize</button>
                          </>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CatalogPanel>
        )}
      </QueryState>
      <NotificationsAdmin />
    </div>
  );
}

function GithubForm({ onDone, onCancel }: { onDone: (message: string) => void; onCancel: () => void }) {
  const [appId, setAppId] = useState("");
  const [installationId, setInstallationId] = useState("");
  const [organization, setOrganization] = useState("");
  const [privateKeyRef, setPrivateKeyRef] = useState("");
  const [privateKey, setPrivateKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      await cloudOpsApi.createGithubIntegration({ appId, installationId, organization, privateKeyRef, privateKey: privateKey || undefined });
      onDone("GitHub App integration saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <CatalogPanel title="Add GitHub App" hint="Paste the private key once. It is never displayed again.">
      <div className="grid gap-3 p-4 md:grid-cols-2">
        <Field label="App ID" value={appId} onChange={setAppId} />
        <Field label="Installation ID" value={installationId} onChange={setInstallationId} />
        <Field label="Organization" value={organization} onChange={setOrganization} />
        <Field label="Existing private key reference" value={privateKeyRef} onChange={setPrivateKeyRef} />
        <label className="text-sm md:col-span-2">Private key (write-only)
          <textarea className="mt-1 w-full rounded border border-outline p-2 font-mono text-xs" rows={4} value={privateKey} onChange={(event) => setPrivateKey(event.target.value)} />
        </label>
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
        <div className="flex gap-2 md:col-span-2">
          <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={onCancel}>Cancel</button>
          <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" disabled={busy} onClick={() => void save()}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </div>
    </CatalogPanel>
  );
}

function AzureForm({ onDone, onCancel }: { onDone: (message: string) => void; onCancel: () => void }) {
  const [organization, setOrganization] = useState("");
  const [project, setProject] = useState("");
  const [authRef, setAuthRef] = useState("");
  const [authSecret, setAuthSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      await cloudOpsApi.createAzureDevOpsIntegration({ organization, project, authRef, authSecret: authSecret || undefined });
      onDone("Azure DevOps integration saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <CatalogPanel title="Add Azure DevOps" hint="PAT or service connection secret is write-only.">
      <div className="grid gap-3 p-4 md:grid-cols-2">
        <Field label="Organization" value={organization} onChange={setOrganization} />
        <Field label="Project" value={project} onChange={setProject} />
        <Field label="Existing auth reference" value={authRef} onChange={setAuthRef} />
        <label className="text-sm">Auth secret (write-only)
          <input type="password" autoComplete="new-password" className="mt-1 w-full rounded border border-outline p-2" value={authSecret} onChange={(event) => setAuthSecret(event.target.value)} />
        </label>
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
        <div className="flex gap-2 md:col-span-2">
          <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={onCancel}>Cancel</button>
          <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" disabled={busy} onClick={() => void save()}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </div>
    </CatalogPanel>
  );
}

function ApplicationsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.managedApplications(signal), [nonce]);
  const envs = useResource((signal) => cloudOpsApi.managedEnvironments(signal), [nonce]);
  const [form, setForm] = useState(false);
  return (
    <>
      {form && envs.status === "success" ? (
        <ApplicationForm environments={envs.data.items} onDone={(message) => { setForm(false); onNotice(message); }} onCancel={() => setForm(false)} />
      ) : null}
      <QueryState state={state} loadingLabel="Loading applications…">
        {(data) => (
          <CatalogPanel title="Applications" hint="Map repositories, pipelines, and Kubernetes workloads per environment.">
            <div className="border-b border-outline p-3">
              <button type="button" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" onClick={() => setForm(true)}>Add Application</button>
            </div>
            {data.items.length === 0 ? (
              <EmptyAction label="No applications configured." action="Add Application" onClick={() => setForm(true)} />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Application</th><th className="p-3">Owner</th><th className="p-3">Repository</th><th className="p-3">Pipeline</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <tr key={row.id} className="border-b border-outline">
                      <td className="p-3 font-semibold">{row.name}</td>
                      <td className="p-3">{row.ownerTeam}</td>
                      <td className="p-3 font-mono text-xs">{row.repositoryId || "—"}</td>
                      <td className="p-3 font-mono text-xs">{row.pipelineId || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CatalogPanel>
        )}
      </QueryState>
    </>
  );
}

function ApplicationForm({
  environments,
  onDone,
  onCancel,
}: {
  environments: ManagedEnvironment[];
  onDone: (message: string) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [ownerTeam, setOwnerTeam] = useState("");
  const [repositoryId, setRepositoryId] = useState("");
  const [pipelineId, setPipelineId] = useState("");
  const [environmentId, setEnvironmentId] = useState(environments[0]?.id || "");
  const [clusterId, setClusterId] = useState("");
  const [namespace, setNamespace] = useState("default");
  const [workload, setWorkload] = useState("");
  const [healthEndpoint, setHealthEndpoint] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      await cloudOpsApi.createApplication({
        name,
        description,
        ownerTeam,
        repositoryId,
        pipelineId,
        environments: environmentId
          ? [{ environmentId, clusterId, namespace, workload, healthEndpoint }]
          : [],
      });
      onDone(`Application ${name} saved`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <CatalogPanel title="Add Application">
      <div className="grid gap-3 p-4 md:grid-cols-2">
        <Field label="Name" value={name} onChange={setName} />
        <Field label="Owner / team" value={ownerTeam} onChange={setOwnerTeam} />
        <Field label="Description" value={description} onChange={setDescription} />
        <Field label="Repository" value={repositoryId} onChange={setRepositoryId} />
        <Field label="Pipeline" value={pipelineId} onChange={setPipelineId} />
        <label className="text-sm">Environment
          <select className="mt-1 w-full rounded border border-outline p-2" value={environmentId} onChange={(event) => setEnvironmentId(event.target.value)}>
            {environments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <Field label="Cluster" value={clusterId} onChange={setClusterId} />
        <Field label="Namespace" value={namespace} onChange={setNamespace} />
        <Field label="Workload" value={workload} onChange={setWorkload} />
        <Field label="Health endpoint" value={healthEndpoint} onChange={setHealthEndpoint} />
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
        <div className="flex gap-2 md:col-span-2">
          <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs" onClick={onCancel}>Cancel</button>
          <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" disabled={busy || !name} onClick={() => void save()}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </div>
    </CatalogPanel>
  );
}

function JobsPanel({ nonce }: { nonce: number }) {
  const state = useResource((signal) => cloudOpsApi.discoveryJobs(signal), [nonce]);
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useResource((signal) => (selected ? cloudOpsApi.discoveryJob(selected, signal) : Promise.resolve(null)), [selected]);
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <div className="xl:col-span-2">
        <QueryState state={state} loadingLabel="Loading discovery jobs…" isEmpty={(data) => data.items.length === 0} emptyLabel="No discovery jobs yet.">
          {(data) => (
            <CatalogPanel title="Discovery Jobs" hint="Queued through Celery. Click a job for correlation and result detail.">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Job</th>
                    <th className="p-3">Provider</th>
                    <th className="p-3">Account</th>
                    <th className="p-3">Environment</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Started</th>
                    <th className="p-3">Finished</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Found</th>
                    <th className="p-3">Errors</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <tr key={row.id} className="border-b border-outline">
                      <td className="p-3"><button type="button" className="font-semibold text-action" onClick={() => setSelected(row.id)}>{row.job}</button></td>
                      <td className="p-3">{row.provider}</td>
                      <td className="p-3">{row.account || "—"}</td>
                      <td className="p-3">{row.environment || "—"}</td>
                      <td className="p-3 font-mono text-xs">{row.type}</td>
                      <td className="p-3 text-xs">{row.started || "—"}</td>
                      <td className="p-3 text-xs">{row.finished || "—"}</td>
                      <td className="p-3"><StatusChip value={row.status} /></td>
                      <td className="p-3">{row.resourcesFound}</td>
                      <td className="p-3">{row.errors}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CatalogPanel>
          )}
        </QueryState>
      </div>
      {selected && detail.status === "success" && detail.data ? (
        <CatalogPanel title="Job details" hint="Correlation ID is returned for every asynchronous action.">
          <div className="space-y-2 p-4 text-sm">
            <Meta label="Status" value={detail.data.status} />
            <Meta label="Correlation" value={detail.data.correlationId} />
            <Meta label="Detail" value={detail.data.detail} />
          </div>
        </CatalogPanel>
      ) : null}
    </div>
  );
}

function SettingsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.platformSettings(signal), [nonce]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const merged = useMemo(() => draft, [draft]);
  return (
    <QueryState state={state} loadingLabel="Loading settings…">
      {(data) => (
        <CatalogPanel title="Platform Settings" hint="Operational schedules and thresholds. Secrets are not stored here.">
          <div className="grid gap-3 p-4 md:grid-cols-2">
            {data.items.map((item) => (
              <label key={item.key} className="text-sm">
                {item.label}
                <input className="mt-1 w-full rounded border border-outline p-2" defaultValue={item.value} onChange={(event) => setDraft((current) => ({ ...current, [item.key]: event.target.value }))} />
              </label>
            ))}
          </div>
          <div className="border-t border-outline p-4">
            <button type="button" className="rounded bg-action px-3 py-1.5 text-xs text-white" onClick={() => void cloudOpsApi.updatePlatformSettings(merged).then(() => onNotice("Platform settings saved"))}>Save settings</button>
          </div>
        </CatalogPanel>
      )}
    </QueryState>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="text-sm">
      {label}
      <input className="mt-1 w-full rounded border border-outline p-2" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase text-muted">{label}</p>
      <p className="mt-1 text-sm">{value}</p>
    </div>
  );
}

function EmptyAction({ label, action, onClick }: { label: string; action: string; onClick: () => void }) {
  return (
    <div className="p-6">
      <p className="text-sm text-muted">{label}</p>
      <button type="button" className="mt-3 rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" onClick={onClick}>{action}</button>
    </div>
  );
}
