"use client";

import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import {
  AdminDialog,
  AdminDrawer,
  AdminField,
  AdminSelect,
  AdminTabs,
  AdminTextarea,
  AdminToast,
  ChoiceCard,
  EmptyCatalog,
  GhostButton,
  Meta,
  PrimaryButton,
  WizardStepper,
  adminInputClass,
} from "@/components/admin/AdminChrome";
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
  "cloud-console",
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
  "cloud-console": "Cloud Credentials",
  jobs: "Discovery Jobs",
  settings: "Platform Settings",
};

const PROVIDER_STEPS = ["Type", "Identity", "Authentication", "Validation", "Review"] as const;

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
      {notice ? <AdminToast message={notice} onDismiss={() => setNotice("")} /> : null}
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <QueryState state={status} loadingLabel="Loading platform status…">
            {(data) =>
              data.onboarding ? (
                <OnboardingCard onStart={() => setSection("providers")} />
              ) : (
                <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
                  <span className="rounded border border-outline bg-white px-2 py-1">Data source {data.dataSource}</span>
                  {data.bootstrapAdmin ? <span className="rounded border border-outline bg-white px-2 py-1">Bootstrap admin enabled</span> : null}
                </div>
              )
            }
          </QueryState>
          <div className="rounded border border-outline bg-white">
            <AdminTabs items={SECTIONS} value={section} labels={LABELS} onChange={setSection} />
          </div>
          {section === "providers" ? <ProvidersPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "accounts" ? <AccountsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "environments" ? <EnvironmentsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "credentials" ? <CredentialsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "applications" ? <ApplicationsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "integrations" ? <IntegrationsPanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "cloud-console" ? <AwsConsolePanel nonce={nonce} onNotice={refresh} /> : null}
          {section === "jobs" ? <JobsPanel nonce={nonce} /> : null}
          {section === "settings" ? <SettingsPanel nonce={nonce} onNotice={refresh} /> : null}
        </div>
      </main>
    </>
  );
}

function OnboardingCard({ onStart }: { onStart: () => void }) {
  return (
    <section className="rounded-lg border border-outline bg-white p-6 shadow-sm">
      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted">Platform onboarding</p>
      <h2 className="mt-1 text-lg font-semibold text-ink">Welcome to CloudOps Platform</h2>
      <p className="mt-2 text-sm text-muted">No cloud providers are configured. Mock infrastructure is disabled.</p>
      <ol className="mt-5 grid gap-3 md:grid-cols-2">
        {ONBOARDING_STEPS.map((step, index) => (
          <li key={step} className="flex gap-3 rounded border border-outline bg-surface-low px-3 py-3 text-sm text-ink">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-action text-[11px] font-bold text-white">
              {index + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
      <button type="button" className="mt-5 rounded bg-action px-4 py-2 text-sm font-semibold text-white" onClick={onStart}>
        Start Setup
      </button>
    </section>
  );
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" onClick={onClick}>
      {label}
    </button>
  );
}

function ProvidersPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.managedProviders(signal), [nonce]);
  const [wizard, setWizard] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <>
      <QueryState state={state} loadingLabel="Loading providers…">
        {(data) => (
          <>
            {data.items.length === 0 ? null : (
              <KpiGrid>
                <Kpi label="Providers" value={data.items.length} />
                <Kpi label="Enabled" value={data.items.filter((item) => item.enabled).length} />
              </KpiGrid>
            )}
            <CatalogPanel
              title="Providers"
              hint="Logical CloudOps configuration. Credentials stay in SecretBackend."
              action={<AddButton label="Add Provider" onClick={() => setWizard(true)} />}
            >
              {data.items.length === 0 ? (
                <EmptyCatalog
                  title="No cloud providers configured"
                  description="Add AWS, Alibaba Cloud, or Microsoft Azure as a logical provider. Credentials are stored separately and never displayed."
                  action="Add Provider"
                  onClick={() => setWizard(true)}
                />
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
                      <tr key={row.id} className="border-b border-outline hover:bg-surface-low/70">
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
      {wizard ? (
        <ProviderWizard
          onDone={(message) => {
            setWizard(false);
            onNotice(message);
          }}
          onCancel={() => setWizard(false)}
        />
      ) : null}
      {selected ? <ProviderDetails id={selected} onClose={() => setSelected(null)} onNotice={onNotice} /> : null}
    </>
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
  const typeOptions = types.status === "success"
    ? types.data.items
    : [
        { id: "AWS", name: "AWS", platform: "EKS", authStrategies: ["AssumeRole", "IAM"], inventorySupported: true },
        { id: "Alibaba", name: "Alibaba Cloud", platform: "ACK", authStrategies: ["RAM", "STS", "AccessKey"], inventorySupported: true },
        { id: "Azure", name: "Microsoft Azure", platform: "AKS", authStrategies: ["ManagedIdentity", "WorkloadIdentity", "ServicePrincipal"], inventorySupported: false },
      ];
  const selectedType = typeOptions.find((item) => item.id === providerType) || typeOptions[0];
  const strategies = selectedType?.authStrategies || [];

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
    <AdminDialog
      title="Add Provider"
      hint="Do not store plaintext credentials on the provider."
      size="xl"
      onClose={onCancel}
      footer={
        <>
          <GhostButton onClick={onCancel}>Cancel</GhostButton>
          {step > 1 ? <GhostButton onClick={() => setStep(step - 1)}>Back</GhostButton> : null}
          {step < 5 ? (
            <PrimaryButton onClick={() => setStep(step + 1)}>Next</PrimaryButton>
          ) : (
            <PrimaryButton disabled={busy} onClick={() => void save()}>
              {busy ? "Saving…" : "Save provider"}
            </PrimaryButton>
          )}
        </>
      }
    >
      <WizardStepper steps={PROVIDER_STEPS} current={step} />
      {step === 1 ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {typeOptions.map((item) => (
            <ChoiceCard
              key={item.id}
              title={item.name}
              description={item.id === "Alibaba"
                ? "China region · ACK clusters · RAM / STS identity."
                : item.id === "Azure"
                  ? "AMER, EMEA, APAC · AKS configuration · inventory adapter pending."
                  : "AMER, EMEA, APAC · EKS clusters · AssumeRole / IAM."}
              selected={providerType === item.id}
              onSelect={() => {
                setProviderType(item.id);
                setName(item.id === "AWS" ? "AWS Corporate" : item.id === "Alibaba" ? "Alibaba China" : "Azure Corporate");
                setAuthStrategy(item.authStrategies[0]);
              }}
            />
          ))}
        </div>
      ) : null}
      {step === 2 ? (
        <div className="grid gap-4 md:grid-cols-2">
          <AdminField label="Name" value={name} onChange={setName} />
          <AdminField label="Description" value={description} onChange={setDescription} />
          <label className="flex items-center gap-2 text-sm text-ink md:col-span-2">
            <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
            Enabled after save
          </label>
        </div>
      ) : null}
      {step === 3 ? (
        <div className="space-y-3">
          <p className="text-xs text-muted">Use a credential reference on the account. Identity metadata is stored without secret values.</p>
          <div className="grid gap-3 sm:grid-cols-3">
            {strategies.map((item) => (
              <ChoiceCard key={item} title={item} description="Identity metadata only. Secret values stay in SecretBackend." selected={authStrategy === item} onSelect={() => setAuthStrategy(item)} />
            ))}
          </div>
          {providerType === "AWS" && authStrategy === "AssumeRole" ? <AwsAssumeRoleHelp /> : null}
        </div>
      ) : null}
      {step === 4 ? (
        <div className="rounded border border-outline bg-surface-low p-4 text-sm text-ink">
          {selectedType?.inventorySupported
            ? "Validation runs after an account is attached. Save the provider first, then add an account and click Validate."
            : "Azure account configuration is available now. Validation and AKS discovery remain disabled until the Azure inventory adapter is added."}
        </div>
      ) : null}
      {step === 5 ? (
        <dl className="grid gap-3 rounded border border-outline bg-surface-low p-4 text-sm md:grid-cols-2">
          <div><dt className="text-[10px] font-bold uppercase text-muted">Name</dt><dd className="mt-1 font-semibold">{name}</dd></div>
          <div><dt className="text-[10px] font-bold uppercase text-muted">Type</dt><dd className="mt-1">{providerType}</dd></div>
          <div><dt className="text-[10px] font-bold uppercase text-muted">Authentication</dt><dd className="mt-1">{authStrategy}</dd></div>
          <div><dt className="text-[10px] font-bold uppercase text-muted">Enabled</dt><dd className="mt-1">{enabled ? "Yes" : "No"}</dd></div>
          <div className="md:col-span-2"><dt className="text-[10px] font-bold uppercase text-muted">Description</dt><dd className="mt-1">{description || "—"}</dd></div>
        </dl>
      ) : null}
      {error ? <p className="mt-4 text-sm text-critical">{error}</p> : null}
    </AdminDialog>
  );
}

function AwsAssumeRoleHelp() {
  return (
    <section className="rounded border border-action/30 bg-action/5 p-4 text-sm text-ink">
      <p className="font-semibold">Local Docker with IAM Identity Center</p>
      <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-muted">
        <li>In AWS IAM, create `CloudOpsDiscoveryRole` using <strong>AWS account - This account</strong> as the trusted entity.</li>
        <li>Attach only the EKS/ACM read-only inline policy from the CloudOps provider onboarding guide.</li>
        <li>On the next account form, enter the account ID, AWS region, and the new role ARN.</li>
        <li>Log in to your AWS SSO profile on the Docker host before validating. The API and worker need that profile mounted at runtime.</li>
      </ol>
      <p className="mt-3 text-xs text-muted">The full policy and cross-provider guidance are documented in `docs/cloud-provider-onboarding.md`.</p>
    </section>
  );
}

function ProviderDetails({ id, onClose, onNotice }: { id: string; onClose: () => void; onNotice: (message: string) => void }) {
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
    <AdminDrawer
      title={state.status === "success" ? state.data.name : "Provider"}
      hint={state.status === "success" ? `${state.data.providerType} · ${state.data.authStrategy}` : "Loading provider details"}
      onClose={onClose}
    >
      <QueryState state={state} loadingLabel="Loading provider…">
        {(row) => (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <Meta label="Accounts" value={String(row.accounts)} />
              <Meta label="Environments" value={String(row.environments)} />
              <Meta label="Clusters" value={String(row.clusters)} />
              <Meta label="Last validation" value={row.validationStatus || "—"} />
              <Meta label="Last discovery" value={row.lastSynchronizedAt || "—"} />
            </div>
            <div className="flex flex-wrap gap-2 border-y border-outline py-4">
              {row.inventorySupported === false ? <p className="text-sm text-muted">Azure AKS validation and discovery require the Azure inventory adapter.</p> : <>
                <PrimaryButton disabled={!!busy} onClick={() => void run("validate")}>{busy === "validate" ? "Validating…" : "Validate Provider"}</PrimaryButton>
                <GhostButton disabled={!!busy} onClick={() => void run("discover")}>{busy === "discover" ? "Starting…" : "Discover All"}</GhostButton>
              </>}
              <GhostButton onClick={() => void run(row.enabled ? "disable" : "enable")}>{row.enabled ? "Disable" : "Enable"}</GhostButton>
            </div>
            <div>
              <h3 className="text-[11px] font-bold uppercase tracking-wide text-muted">Accounts</h3>
              <ul className="mt-2 divide-y divide-outline rounded border border-outline text-sm">
                {(row.accountsDetail || []).length === 0 ? <li className="p-3 text-muted">No accounts attached.</li> : (row.accountsDetail || []).map((item) => (
                  <li key={item.id} className="flex justify-between p-3"><span>{item.name}</span><StatusChip value={item.readiness} /></li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-[11px] font-bold uppercase tracking-wide text-muted">Environments</h3>
              <ul className="mt-2 divide-y divide-outline rounded border border-outline text-sm">
                {(row.environmentsDetail || []).length === 0 ? <li className="p-3 text-muted">No environments attached.</li> : (row.environmentsDetail || []).map((item) => (
                  <li key={item.id} className="flex justify-between p-3"><span>{item.name}</span><StatusChip value={item.readiness} /></li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </QueryState>
    </AdminDrawer>
  );
}

function AccountsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const providers = useResource((signal) => cloudOpsApi.managedProviders(signal), [nonce]);
  const accounts = useResource((signal) => cloudOpsApi.managedAccounts(signal), [nonce]);
  const [form, setForm] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <>
      <QueryState state={accounts} loadingLabel="Loading accounts…">
        {(data) => (
          <CatalogPanel
            title="Cloud Accounts"
            hint="NONPROD / PROD class. Secrets stay in SecretBackend."
            action={<AddButton label="Add Account" onClick={() => setForm(true)} />}
          >
            {data.items.length === 0 ? (
              <EmptyCatalog
                title="No cloud accounts configured"
                description="Attach a NONPROD or PROD account to a provider. Access keys are write-only."
                action="Add Account"
                onClick={() => setForm(true)}
              />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Account</th><th className="p-3">Provider</th><th className="p-3">Region</th><th className="p-3">Class</th><th className="p-3">Readiness</th><th className="p-3">Clusters</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row: ManagedAccount) => (
                    <tr key={row.id} className="border-b border-outline hover:bg-surface-low/70">
                      <td className="p-3"><button type="button" className="font-semibold text-action hover:underline" onClick={() => setSelected(row.id)}>{row.name}</button></td>
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
      {form && providers.status === "success" ? (
        <AccountForm providers={providers.data.items} onDone={(message) => { setForm(false); onNotice(message); }} onCancel={() => setForm(false)} />
      ) : null}
      {selected ? <AccountDetails id={selected} onClose={() => setSelected(null)} onNotice={onNotice} /> : null}
    </>
  );
}

function AccountForm({ providers, onDone, onCancel }: { providers: ManagedProvider[]; onDone: (message: string) => void; onCancel: () => void }) {
  const first = providers[0];
  const [providerId, setProviderId] = useState(first?.id || "");
  const selected = providers.find((item) => item.id === providerId);
  const alibaba = selected?.providerType === "Alibaba";
  const azure = selected?.providerType === "Azure";
  const [name, setName] = useState(alibaba ? "Alibaba China NonProd" : azure ? "Azure EMEA NonProd" : "AWS EMEA NonProd");
  const [accountId, setAccountId] = useState("");
  const [region, setRegion] = useState(alibaba ? "China" : "EMEA");
  const [cloudRegion, setCloudRegion] = useState(alibaba ? "cn-hangzhou" : azure ? "westeurope" : "eu-west-1");
  const [roleArn, setRoleArn] = useState("");
  const [externalId, setExternalId] = useState("");
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
          provider: alibaba ? "alibaba" : azure ? "azure" : "aws",
          region: region.toLowerCase(),
          account: name.toLowerCase().replace(/\s+/g, "-"),
          environment: accountClass === "PROD" ? "prd" : "dev",
          credentialType: alibaba ? "ram_role" : azure ? "application" : "sts_assume_role",
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
        externalId: alibaba || azure ? undefined : externalId || undefined,
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
    <AdminDialog
      title="Add Account"
      hint="Access keys and webhook URLs are write-only."
      size="xl"
      onClose={onCancel}
      footer={
        <>
          <GhostButton onClick={onCancel}>Cancel</GhostButton>
          <PrimaryButton disabled={busy || !providerId} onClick={() => void save()}>{busy ? "Saving…" : "Save account"}</PrimaryButton>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-2">
        <AdminSelect label="Provider" value={providerId} onChange={(id) => {
          const provider = providers.find((item) => item.id === id);
          setProviderId(id);
          if (provider?.providerType === "Alibaba") {
            setName("Alibaba China NonProd");
            setRegion("China");
            setCloudRegion("cn-hangzhou");
          } else if (provider?.providerType === "Azure") {
            setName("Azure EMEA NonProd");
            setRegion("EMEA");
            setCloudRegion("westeurope");
          } else {
            setName("AWS EMEA NonProd");
            setRegion("EMEA");
            setCloudRegion("eu-west-1");
          }
        }}>
          {providers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </AdminSelect>
        <AdminField label="Account name" value={name} onChange={setName} />
        <AdminField label={alibaba ? "Alibaba account ID" : azure ? "Azure subscription ID" : "AWS account ID"} value={accountId} onChange={(value) => {
          setAccountId(value);
          if (!alibaba && !azure && (!roleArn || roleArn.endsWith(":role/CloudOpsDiscoveryRole"))) {
            setRoleArn(value ? `arn:aws:iam::${value}:role/CloudOpsDiscoveryRole` : "");
          }
        }} />
        <AdminField label="Logical region" value={region} onChange={setRegion} />
        <AdminField label="Cloud region" value={cloudRegion} onChange={setCloudRegion} />
        <AdminField label={alibaba ? "RAM role" : azure ? "Managed identity or application ID" : "Role ARN"} value={roleArn} onChange={setRoleArn} />
        {!alibaba && !azure ? <AdminField label="External ID (optional)" value={externalId} onChange={setExternalId} /> : null}
        <AdminSelect label="Account class" value={accountClass} onChange={setAccountClass}>
          <option value="NONPROD">NONPROD</option>
          <option value="PROD">PROD</option>
        </AdminSelect>
        <AdminField label="Existing credential reference" value={credentialRef} onChange={setCredentialRef} />
        <AdminField label="New secret material (write-only)" value={secretValue} onChange={setSecretValue} type="password" autoComplete="new-password" className="md:col-span-2" />
        {!alibaba && !azure ? <p className="-mt-2 text-xs text-muted md:col-span-2">Leave External ID empty for an AWS role trusted by this account. Use it only when a third-party trust policy requires it.</p> : null}
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
      </div>
    </AdminDialog>
  );
}

function AccountDetails({ id, onClose, onNotice }: { id: string; onClose: () => void; onNotice: (message: string) => void }) {
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
    <AdminDrawer
      title={state.status === "success" ? state.data.name : "Account"}
      hint={state.status === "success" ? `${state.data.provider} · ${state.data.authStrategy || "AssumeRole"}` : "Loading account details"}
      onClose={onClose}
    >
      <QueryState state={state} loadingLabel="Loading account…">
        {(row) => (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <Meta label="Account ID" value={row.accountId || "—"} />
              <Meta label="Role" value={row.roleArn || row.ramRole || "—"} />
              <Meta label="Environments" value={(row.hostedEnvironments || []).join(" ") || "—"} />
              <Meta label="Last validation" value={row.validationStatus || "—"} />
            </div>
            <div className="flex flex-wrap gap-2 border-y border-outline py-4">
              {row.inventorySupported === false ? <p className="text-sm text-muted">Azure AKS validation and discovery require the Azure inventory adapter.</p> : <>
                <PrimaryButton disabled={!!busy} onClick={() => void run("validate")}>{busy === "validate" ? "Validating…" : "Validate"}</PrimaryButton>
                <GhostButton disabled={!!busy} onClick={() => void run("discover")}>{busy === "discover" ? "Starting…" : "Discover"}</GhostButton>
              </>}
              <GhostButton
                onClick={() => {
                  if (window.confirm(`Delete ${row.name} if unused?`)) {
                    void cloudOpsApi.deleteAccount(id).then(() => { onNotice(`Account ${row.name} deleted`); onClose(); }).catch((error) => onNotice(error instanceof Error ? error.message : "Delete failed"));
                  }
                }}
              >
                Delete if unused
              </GhostButton>
            </div>
          </div>
        )}
      </QueryState>
    </AdminDrawer>
  );
}

function EnvironmentsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const accounts = useResource((signal) => cloudOpsApi.managedAccounts(signal), [nonce]);
  const envs = useResource((signal) => cloudOpsApi.managedEnvironments(signal), [nonce]);
  const [form, setForm] = useState(false);
  return (
    <>
      <QueryState state={envs} loadingLabel="Loading environments…">
        {(data) => (
          <CatalogPanel
            title="Environments"
            hint="Environment class is configurable. PRD is visually distinct."
            action={<AddButton label="Add Environment" onClick={() => setForm(true)} />}
          >
            {data.items.length === 0 ? (
              <EmptyCatalog
                title="No environments configured"
                description="Map DEV, INT/TST, UAT, NPD, and PRD onto a cloud account. Production remains visually distinct."
                action="Add Environment"
                onClick={() => setForm(true)}
              />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Name</th><th className="p-3">Class</th><th className="p-3">Provider</th><th className="p-3">Region</th><th className="p-3">Account</th><th className="p-3">Readiness</th><th className="p-3" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row: ManagedEnvironment) => (
                    <tr key={row.id} className={row.environment === "PRD" ? "border-b border-prd/30 bg-prd/5" : "border-b border-outline hover:bg-surface-low/70"}>
                      <td className="p-3 font-semibold">{row.name}</td>
                      <td className="p-3">{row.environment}</td>
                      <td className="p-3">{row.provider}</td>
                      <td className="p-3">{row.region}</td>
                      <td className="p-3 font-mono text-xs">{row.account}</td>
                      <td className="p-3"><StatusChip value={row.readiness} /></td>
                      <td className="p-3">
                        <button type="button" className="mr-2 text-xs font-semibold text-action hover:underline" onClick={() => void cloudOpsApi.discoverEnvironment(row.id).then((result) => onNotice(`Cluster discovery started. Job ${result.jobId}`))}>Discover Clusters</button>
                        <button type="button" className="text-xs text-muted hover:underline" onClick={() => void cloudOpsApi.updateEnvironment(row.id, { enabled: !row.enabled }).then(() => onNotice(`Environment ${row.enabled ? "disabled" : "enabled"}`))}>{row.enabled ? "Disable" : "Enable"}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CatalogPanel>
        )}
      </QueryState>
      {form && accounts.status === "success" ? (
        <EnvironmentForm accounts={accounts.data.items} onDone={(message) => { setForm(false); onNotice(message); }} onCancel={() => setForm(false)} />
      ) : null}
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
    <AdminDialog
      title="Add Environment"
      hint="PRD is visually distinct and never mixed with non-production."
      onClose={onCancel}
      footer={
        <>
          <GhostButton onClick={onCancel}>Cancel</GhostButton>
          <PrimaryButton disabled={busy || !accountId} onClick={() => void save()}>{busy ? "Saving…" : "Save environment"}</PrimaryButton>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-2">
        <AdminSelect label="Cloud account" value={accountId} onChange={setAccountId}>
          {accounts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </AdminSelect>
        <AdminSelect label="Environment class" value={environmentClass} onChange={(value) => { setEnvironmentClass(value); setName(value); }}>
          {["DEV", "INT/TST", "UAT", "NPD", "PRD"].map((item) => <option key={item} value={item}>{item}</option>)}
        </AdminSelect>
        <AdminField label="Name" value={name} onChange={setName} />
        <AdminField label="Description" value={description} onChange={setDescription} />
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
      </div>
    </AdminDialog>
  );
}

function CredentialsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.credentials({}, signal), [nonce]);
  const [form, setForm] = useState(false);
  const [historyId, setHistoryId] = useState<string | null>(null);
  const history = useResource((signal) => (historyId ? cloudOpsApi.credentialHistory(historyId, signal) : Promise.resolve(null)), [historyId]);
  return (
    <>
      <QueryState state={state} loadingLabel="Loading credentials…">
        {(data) => (
          <CatalogPanel
            title="Credentials"
            hint="Write-only secret material. Existing values are never shown."
            action={<AddButton label="Add Credential" onClick={() => setForm(true)} />}
          >
            {data.items.length === 0 ? (
              <EmptyCatalog
                title="No credentials configured"
                description="Store identity references in SecretBackend. Secret values cannot be retrieved after save."
                action="Add Credential"
                onClick={() => setForm(true)}
              />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Name</th><th className="p-3">Type</th><th className="p-3">Scope</th><th className="p-3">Status</th><th className="p-3" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <tr key={row.id} className="border-b border-outline hover:bg-surface-low/70">
                      <td className="p-3 font-semibold">{row.name}</td>
                      <td className="p-3">{row.credentialType}</td>
                      <td className="p-3 font-mono text-xs">{row.provider} / {row.region} / {row.environment}</td>
                      <td className="p-3"><StatusChip value={row.status} /></td>
                      <td className="p-3 space-x-2">
                        <button type="button" className="text-xs text-action hover:underline" onClick={() => void cloudOpsApi.validateCredential(row.id).then((result) => onNotice(`Credential validation queued. Job ${result.jobId}`))}>Validate</button>
                        <button type="button" className="text-xs text-action hover:underline" onClick={() => setHistoryId(row.id)}>History</button>
                        <button type="button" className="text-xs text-muted hover:underline" onClick={() => void cloudOpsApi.updateCredential(row.id, { status: "DISABLED" }).then(() => onNotice(`Credential ${row.name} disabled`))}>Disable</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CatalogPanel>
        )}
      </QueryState>
      {form ? <CredentialForm onDone={(message) => { setForm(false); onNotice(message); }} onCancel={() => setForm(false)} /> : null}
      {historyId ? (
        <AdminDrawer title="Credential history" hint="Audit events only. Secret values are never stored here." onClose={() => setHistoryId(null)}>
          {history.status === "success" && history.data ? (
            <ul className="divide-y divide-outline rounded border border-outline">
              {history.data.items.length === 0 ? (
                <li className="p-3 text-sm text-muted">No history recorded.</li>
              ) : (
                history.data.items.map((item) => (
                  <li key={item.id} className="p-3">
                    <p className="text-sm font-semibold text-ink">{item.action} · {item.result}</p>
                    <p className="mt-0.5 text-xs text-muted">{item.detail}</p>
                    <p className="mt-1 font-mono text-[11px] text-muted">{item.createdAt}</p>
                  </li>
                ))
              )}
            </ul>
          ) : (
            <p className="text-sm text-muted">Loading history…</p>
          )}
        </AdminDrawer>
      ) : null}
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
    <AdminDialog
      title="Add Credential"
      hint="Secret material is write-only and stored in SecretBackend."
      size="xl"
      onClose={onCancel}
      footer={
        <>
          <GhostButton onClick={onCancel}>Cancel</GhostButton>
          <PrimaryButton disabled={busy || !name} onClick={() => void save()}>{busy ? "Saving…" : "Save credential"}</PrimaryButton>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-2">
        <AdminField label="Name" value={name} onChange={setName} />
        <AdminSelect label="Provider" value={provider} onChange={setProvider}>
          <option>AWS</option>
          <option>Alibaba</option>
        </AdminSelect>
        <AdminField label="Region" value={region} onChange={setRegion} />
        <AdminField label="Account alias" value={account} onChange={setAccount} />
        <AdminSelect label="Environment" value={environment} onChange={setEnvironment}>
          {["DEV", "INT/TST", "UAT", "NPD", "PRD"].map((item) => <option key={item}>{item}</option>)}
        </AdminSelect>
        <AdminSelect label="Type" value={credentialType} onChange={setCredentialType}>
          <option value="sts_assume_role">STS AssumeRole</option>
          <option value="iam_role">IAM role</option>
          <option value="ram_role">RAM role</option>
          <option value="access_key">Access key</option>
        </AdminSelect>
        <AdminField label="Role ARN / RAM role" value={roleArn} onChange={setRoleArn} />
        <AdminField label="Secret material (write-only)" value={secretValue} onChange={setSecretValue} type="password" autoComplete="new-password" className="md:col-span-2" />
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
      </div>
    </AdminDialog>
  );
}

function IntegrationsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.adminIntegrations(signal), [nonce]);
  const [github, setGithub] = useState(false);
  const [azure, setAzure] = useState(false);
  return (
    <div className="space-y-6">
      <QueryState state={state} loadingLabel="Loading integrations…">
        {(data) => (
          <CatalogPanel
            title="Integrations"
            hint="GitHub, Azure DevOps, and notification destinations. Tokens stay in SecretBackend."
            action={
              <div className="flex gap-2">
                <AddButton label="Add GitHub App" onClick={() => setGithub(true)} />
                <button type="button" className="rounded border border-outline bg-white px-3 py-1.5 text-xs font-semibold" onClick={() => setAzure(true)}>Add Azure DevOps</button>
              </div>
            }
          >
            {data.items.length === 0 ? (
              <EmptyCatalog
                title="No integrations configured"
                description="Connect GitHub Apps or Azure DevOps. Private keys and PATs are write-only."
                action="Add GitHub App"
                onClick={() => setGithub(true)}
              />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Integration</th><th className="p-3">Type</th><th className="p-3">Status</th><th className="p-3">Scope</th><th className="p-3" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <tr key={row.id} className="border-b border-outline hover:bg-surface-low/70">
                      <td className="p-3 font-semibold">{row.name}</td>
                      <td className="p-3">{row.type || ""}</td>
                      <td className="p-3"><StatusChip value={row.status} /></td>
                      <td className="p-3">{row.scope}</td>
                      <td className="p-3 space-x-2">
                        {row.type === "github" ? (
                          <>
                            <button type="button" className="text-xs text-action hover:underline" onClick={() => void cloudOpsApi.validateGithubIntegration(row.id).then((result) => onNotice(result.connected ? "GitHub validation succeeded" : result.detail))}>Validate</button>
                            <button type="button" className="text-xs text-action hover:underline" onClick={() => void cloudOpsApi.triggerGithubSync().then(() => onNotice("GitHub synchronize started"))}>Synchronize</button>
                            <button type="button" className="text-xs text-muted hover:underline" onClick={() => void cloudOpsApi.updateGithubIntegration(row.id, { enabled: false }).then(() => onNotice("GitHub integration disabled"))}>Disable</button>
                          </>
                        ) : null}
                        {row.type === "azure_devops" ? (
                          <>
                            <button type="button" className="text-xs text-action hover:underline" onClick={() => void cloudOpsApi.validateAzureDevOpsIntegration(row.id).then((result) => onNotice(result.connected ? "Azure DevOps validation succeeded" : result.detail))}>Validate</button>
                            <button type="button" className="text-xs text-action hover:underline" onClick={() => void cloudOpsApi.triggerPipelineSync().then(() => onNotice("Pipeline synchronize started"))}>Synchronize</button>
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
      <NotificationsAdmin onNotice={onNotice} />
      {github ? <GithubForm onDone={(message) => { setGithub(false); onNotice(message); }} onCancel={() => setGithub(false)} /> : null}
      {azure ? <AzureForm onDone={(message) => { setAzure(false); onNotice(message); }} onCancel={() => setAzure(false)} /> : null}
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
    <AdminDialog
      title="Add GitHub App"
      hint="Paste the private key once. It is never displayed again."
      size="xl"
      onClose={onCancel}
      footer={
        <>
          <GhostButton onClick={onCancel}>Cancel</GhostButton>
          <PrimaryButton disabled={busy} onClick={() => void save()}>{busy ? "Saving…" : "Save GitHub App"}</PrimaryButton>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-2">
        <AdminField label="App ID" value={appId} onChange={setAppId} />
        <AdminField label="Installation ID" value={installationId} onChange={setInstallationId} />
        <AdminField label="Organization" value={organization} onChange={setOrganization} />
        <AdminField label="Existing private key reference" value={privateKeyRef} onChange={setPrivateKeyRef} />
        <AdminTextarea label="Private key (write-only)" value={privateKey} onChange={setPrivateKey} className="md:col-span-2" />
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
      </div>
    </AdminDialog>
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
    <AdminDialog
      title="Add Azure DevOps"
      hint="PAT or service connection secret is write-only."
      onClose={onCancel}
      footer={
        <>
          <GhostButton onClick={onCancel}>Cancel</GhostButton>
          <PrimaryButton disabled={busy} onClick={() => void save()}>{busy ? "Saving…" : "Save Azure DevOps"}</PrimaryButton>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-2">
        <AdminField label="Organization" value={organization} onChange={setOrganization} />
        <AdminField label="Project" value={project} onChange={setProject} />
        <AdminField label="Existing auth reference" value={authRef} onChange={setAuthRef} />
        <AdminField label="Auth secret (write-only)" value={authSecret} onChange={setAuthSecret} type="password" autoComplete="new-password" />
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
      </div>
    </AdminDialog>
  );
}

function ApplicationsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.managedApplications(signal), [nonce]);
  const envs = useResource((signal) => cloudOpsApi.managedEnvironments(signal), [nonce]);
  const [form, setForm] = useState(false);
  return (
    <>
      <QueryState state={state} loadingLabel="Loading applications…">
        {(data) => (
          <CatalogPanel
            title="Applications"
            hint="Map repositories, pipelines, and Kubernetes workloads per environment."
            action={<AddButton label="Add Application" onClick={() => setForm(true)} />}
          >
            {data.items.length === 0 ? (
              <EmptyCatalog
                title="No applications configured"
                description="Map a repository and pipeline to an environment workload. Secret values are never shown."
                action="Add Application"
                onClick={() => setForm(true)}
              />
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                    <th className="p-3">Application</th><th className="p-3">Owner</th><th className="p-3">Repository</th><th className="p-3">Pipeline</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <tr key={row.id} className="border-b border-outline hover:bg-surface-low/70">
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
      {form && envs.status === "success" ? (
        <ApplicationForm environments={envs.data.items} onDone={(message) => { setForm(false); onNotice(message); }} onCancel={() => setForm(false)} />
      ) : null}
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
    <AdminDialog
      title="Add Application"
      hint="Map repository, pipeline, and Kubernetes workload without storing secrets."
      size="xl"
      onClose={onCancel}
      footer={
        <>
          <GhostButton onClick={onCancel}>Cancel</GhostButton>
          <PrimaryButton disabled={busy || !name} onClick={() => void save()}>{busy ? "Saving…" : "Save application"}</PrimaryButton>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-2">
        <AdminField label="Name" value={name} onChange={setName} />
        <AdminField label="Owner / team" value={ownerTeam} onChange={setOwnerTeam} />
        <AdminField label="Description" value={description} onChange={setDescription} />
        <AdminField label="Repository" value={repositoryId} onChange={setRepositoryId} />
        <AdminField label="Pipeline" value={pipelineId} onChange={setPipelineId} />
        <AdminSelect label="Environment" value={environmentId} onChange={setEnvironmentId}>
          {environments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </AdminSelect>
        <AdminField label="Cluster" value={clusterId} onChange={setClusterId} />
        <AdminField label="Namespace" value={namespace} onChange={setNamespace} />
        <AdminField label="Workload" value={workload} onChange={setWorkload} />
        <AdminField label="Health endpoint" value={healthEndpoint} onChange={setHealthEndpoint} />
        {error ? <p className="text-sm text-critical md:col-span-2">{error}</p> : null}
      </div>
    </AdminDialog>
  );
}

function JobsPanel({ nonce }: { nonce: number }) {
  const state = useResource((signal) => cloudOpsApi.discoveryJobs(signal), [nonce]);
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useResource((signal) => (selected ? cloudOpsApi.discoveryJob(selected, signal) : Promise.resolve(null)), [selected]);
  return (
    <>
      <QueryState state={state} loadingLabel="Loading discovery jobs…" isEmpty={(data) => data.items.length === 0} emptyLabel="No discovery jobs yet.">
        {(data) => (
          <CatalogPanel title="Discovery Jobs" hint="Queued through Celery. Open a job for correlation and result detail.">
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
                  <tr key={row.id} className="border-b border-outline hover:bg-surface-low/70">
                    <td className="p-3"><button type="button" className="font-semibold text-action hover:underline" onClick={() => setSelected(row.id)}>{row.job}</button></td>
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
      {selected ? (
        <AdminDrawer title="Job details" hint="Correlation ID is returned for every asynchronous action." onClose={() => setSelected(null)}>
          {detail.status === "success" && detail.data ? (
            <div className="space-y-4">
              <Meta label="Status" value={detail.data.status} />
              <Meta label="Correlation" value={detail.data.correlationId} />
              <Meta label="Detail" value={detail.data.detail} />
            </div>
          ) : (
            <p className="text-sm text-muted">Loading job…</p>
          )}
        </AdminDrawer>
      ) : null}
    </>
  );
}

function SettingsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const state = useResource((signal) => cloudOpsApi.platformSettings(signal), [nonce]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const merged = useMemo(() => draft, [draft]);
  return (
    <QueryState state={state} loadingLabel="Loading settings…">
      {(data) => (
        <CatalogPanel
          title="Platform Settings"
          hint="Operational schedules and thresholds. Secrets are not stored here."
          action={
            <PrimaryButton onClick={() => void cloudOpsApi.updatePlatformSettings(merged).then(() => onNotice("Platform settings saved"))}>
              Save settings
            </PrimaryButton>
          }
        >
          <div className="grid gap-4 p-5 md:grid-cols-2">
            {data.items.map((item) => (
              <label key={item.key} className="block space-y-1 text-sm">
                <span className="text-[11px] font-bold uppercase tracking-wide text-muted">{item.label}</span>
                <input className={adminInputClass} defaultValue={item.value} onChange={(event) => setDraft((current) => ({ ...current, [item.key]: event.target.value }))} />
              </label>
            ))}
          </div>
        </CatalogPanel>
      )}
    </QueryState>
  );
}

/* ------------------------------------------------------------------ */
/*  AWS Console – configure credentials, validate, test S3 listing    */
/* ------------------------------------------------------------------ */

function AwsConsolePanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const credStatus = useResource((signal) => cloudOpsApi.awsCredentialsStatus(signal), [nonce]);
  const [accessKeyId, setAccessKeyId] = useState("");
  const [secretAccessKey, setSecretAccessKey] = useState("");
  const [sessionToken, setSessionToken] = useState("");
  const [region, setRegion] = useState("eu-west-1");
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ valid: boolean; account: string; arn: string; error?: string } | null>(null);
  const [buckets, setBuckets] = useState<{ items: Array<{ name: string; createdAt?: string | null; account: string; accountId: string }>; errors: Array<{ account: string; accountId: string; detail: string }> } | null>(null);
  const [loadingBuckets, setLoadingBuckets] = useState(false);

  async function handleSave() {
    if (!accessKeyId || !secretAccessKey) return;
    setSaving(true);
    setResult(null);
    try {
      const response = await cloudOpsApi.configureAwsCredentials({
        accessKeyId,
        secretAccessKey,
        sessionToken: sessionToken || undefined,
        region,
      });
      setResult(response);
      if (response.valid) {
        onNotice(`AWS credentials configured — account ${response.account}`);
        setAccessKeyId("");
        setSecretAccessKey("");
        setSessionToken("");
      }
    } catch (error) {
      setResult({ valid: false, account: "", arn: "", error: String(error) });
    } finally {
      setSaving(false);
    }
  }

  async function handleTestS3() {
    setLoadingBuckets(true);
    setBuckets(null);
    try {
      const data = await cloudOpsApi.storageBuckets();
      setBuckets(data);
    } catch (error) {
      setBuckets({ items: [], errors: [{ account: "-", accountId: "-", detail: String(error) }] });
    } finally {
      setLoadingBuckets(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Current status */}
      <CatalogPanel title="AWS Credentials Status" hint="Current state of local AWS credentials (~/.aws/credentials). Secret values are never displayed.">
        <QueryState state={credStatus} loadingLabel="Checking credentials…">
          {(data) => (
            <div className="p-4">
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center gap-2">
                  <span className={`inline-block h-2.5 w-2.5 rounded-full ${data.valid ? "bg-emerald-500" : data.configured ? "bg-amber-500" : "bg-zinc-300"}`} />
                  <span className="text-sm font-semibold">{data.valid ? "Valid" : data.configured ? "Invalid / Expired" : "Not Configured"}</span>
                </div>
                {data.account ? <span className="rounded bg-surface-low px-2 py-0.5 text-xs font-mono">Account: {data.account}</span> : null}
                {data.principal ? <span className="rounded bg-surface-low px-2 py-0.5 text-xs font-mono">Principal: {data.principal}</span> : null}
                {data.profiles?.length ? <span className="rounded bg-surface-low px-2 py-0.5 text-xs">Profiles: {data.profiles.join(", ")}</span> : null}
              </div>
              {data.error ? <p className="mt-2 text-xs text-critical">{data.error}</p> : null}
            </div>
          )}
        </QueryState>
      </CatalogPanel>

      {/* Configure credentials form */}
      <CatalogPanel title="Configure AWS Credentials" hint="Enter your AWS access keys. Values are written to ~/.aws/credentials and validated with STS.">
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <AdminField label="Access Key ID" value={accessKeyId} onChange={setAccessKeyId} />
            <AdminField label="Secret Access Key" value={secretAccessKey} onChange={setSecretAccessKey} />
            <AdminField label="Session Token (optional)" value={sessionToken} onChange={setSessionToken} />
            <AdminSelect label="Region" value={region} onChange={setRegion}>
              <option value="eu-west-1">eu-west-1 (Ireland)</option>
              <option value="eu-north-1">eu-north-1 (Stockholm)</option>
              <option value="us-east-1">us-east-1 (N. Virginia)</option>
              <option value="us-west-2">us-west-2 (Oregon)</option>
              <option value="ap-southeast-1">ap-southeast-1 (Singapore)</option>
              <option value="ap-northeast-1">ap-northeast-1 (Tokyo)</option>
              <option value="cn-hangzhou">cn-hangzhou (China)</option>
            </AdminSelect>
          </div>
          <div className="flex items-center gap-3">
            <PrimaryButton disabled={saving || !accessKeyId || !secretAccessKey} onClick={handleSave}>{saving ? "Saving…" : "Save & Validate"}</PrimaryButton>
            <GhostButton disabled={loadingBuckets} onClick={handleTestS3}>Test S3 Buckets</GhostButton>
          </div>

          {/* Validation result */}
          {result ? (
            <div className={`rounded border p-3 text-sm ${result.valid ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-red-300 bg-red-50 text-red-800"}`}>
              {result.valid ? (
                <p>✓ Credentials valid — AWS Account <strong>{result.account}</strong>, Identity <code className="text-xs">{result.arn}</code></p>
              ) : (
                <p>✗ Validation failed: {result.error}</p>
              )}
            </div>
          ) : null}
        </div>
      </CatalogPanel>

      {/* S3 bucket listing results */}
      {loadingBuckets ? (
        <CatalogPanel title="S3 Buckets"><p className="p-4 text-sm text-muted">Loading buckets…</p></CatalogPanel>
      ) : buckets ? (
        <CatalogPanel title={`S3 Buckets (${buckets.items.length})`} hint="Bucket metadata from all enabled AWS accounts.">
          {buckets.errors.length > 0 ? (
            <div className="border-b border-outline bg-red-50 p-3">
              {buckets.errors.map((err, i) => (
                <p key={i} className="text-xs text-red-700">
                  <strong>{err.account}</strong> ({err.accountId}): {err.detail}
                </p>
              ))}
            </div>
          ) : null}
          {buckets.items.length > 0 ? (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
                  <th className="p-3">Bucket Name</th>
                  <th className="p-3">Created</th>
                  <th className="p-3">Account</th>
                  <th className="p-3">Account ID</th>
                </tr>
              </thead>
              <tbody>
                {buckets.items.map((b) => (
                  <tr key={b.name} className="border-b border-outline hover:bg-surface-low/70">
                    <td className="p-3 font-mono text-xs">{b.name}</td>
                    <td className="p-3 text-xs text-muted">{b.createdAt ?? "—"}</td>
                    <td className="p-3">{b.account}</td>
                    <td className="p-3 font-mono text-xs">{b.accountId}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : buckets.errors.length === 0 ? (
            <p className="p-4 text-sm text-muted">No buckets found.</p>
          ) : null}
        </CatalogPanel>
      ) : null}

      <AlibabaCredentialsPanel nonce={nonce} onNotice={onNotice} />
    </div>
  );
}

function AlibabaCredentialsPanel({ nonce, onNotice }: { nonce: number; onNotice: (message: string) => void }) {
  const credStatus = useResource((signal) => cloudOpsApi.alibabaCredentialsStatus(signal), [nonce]);
  const [accessKeyId, setAccessKeyId] = useState("");
  const [accessKeySecret, setAccessKeySecret] = useState("");
  const [region, setRegion] = useState("cn-hangzhou");
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ valid: boolean; account: string; arn: string; error?: string } | null>(null);

  async function handleSave() {
    if (!accessKeyId || !accessKeySecret) return;
    setSaving(true);
    setResult(null);
    try {
      const response = await cloudOpsApi.configureAlibabaCredentials({ accessKeyId, accessKeySecret, region });
      setResult(response);
      if (response.valid) {
        onNotice(`Alibaba credentials configured — account ${response.account}`);
        setAccessKeyId("");
        setAccessKeySecret("");
      }
    } catch (error) {
      setResult({ valid: false, account: "", arn: "", error: String(error) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <CatalogPanel title="Alibaba Credentials Status" hint="Stored in ~/.aliyun/credentials. Secret values are never displayed.">
        <QueryState state={credStatus} loadingLabel="Checking Alibaba credentials…">
          {(data) => (
            <div className="p-4">
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center gap-2">
                  <span className={`inline-block h-2.5 w-2.5 rounded-full ${data.valid ? "bg-emerald-500" : data.configured ? "bg-amber-500" : "bg-zinc-300"}`} />
                  <span className="text-sm font-semibold">{data.valid ? "Valid" : data.configured ? "Invalid" : "Not Configured"}</span>
                </div>
                {data.account ? <span className="rounded bg-surface-low px-2 py-0.5 text-xs font-mono">Account: {data.account}</span> : null}
                {data.principal ? <span className="rounded bg-surface-low px-2 py-0.5 text-xs font-mono">Principal: {data.principal}</span> : null}
              </div>
              {data.error ? <p className="mt-2 text-xs text-critical">{data.error}</p> : null}
            </div>
          )}
        </QueryState>
      </CatalogPanel>
      <CatalogPanel title="Configure Alibaba Credentials" hint="AccessKey is written to ~/.aliyun/credentials and validated with STS.">
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <AdminField label="Access Key ID" value={accessKeyId} onChange={setAccessKeyId} />
            <AdminField label="Access Key Secret" value={accessKeySecret} onChange={setAccessKeySecret} />
            <AdminSelect label="Region" value={region} onChange={setRegion}>
              <option value="cn-hangzhou">cn-hangzhou</option>
              <option value="cn-shanghai">cn-shanghai</option>
              <option value="cn-beijing">cn-beijing</option>
              <option value="cn-shenzhen">cn-shenzhen</option>
            </AdminSelect>
          </div>
          <PrimaryButton disabled={saving || !accessKeyId || !accessKeySecret} onClick={handleSave}>
            {saving ? "Saving…" : "Save & Validate"}
          </PrimaryButton>
          {result ? (
            <div className={`rounded border p-3 text-sm ${result.valid ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-red-300 bg-red-50 text-red-800"}`}>
              {result.valid ? (
                <p>✓ Credentials valid — Alibaba Account <strong>{result.account}</strong></p>
              ) : (
                <p>✗ Validation failed: {result.error}</p>
              )}
            </div>
          ) : null}
        </div>
      </CatalogPanel>
    </>
  );
}
