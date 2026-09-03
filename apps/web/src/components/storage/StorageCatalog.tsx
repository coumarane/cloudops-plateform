"use client";

import { PageHeader } from "@/components/layout/PageHeader";
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";

export function StorageCatalog() {
  const state = useResource((signal) => cloudOpsApi.storageBuckets(signal), []);

  return (
    <>
      <PageHeader title="Storage" subtitle="Read-only S3 bucket inventory through configured AWS AssumeRole accounts." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-5">
          <QueryState state={state} loadingLabel="Listing S3 buckets…">
            {(data) => (
              <>
                {data.errors.length ? (
                  <section className="rounded border border-warning/50 bg-warning/10 p-4 text-sm text-ink">
                    <p className="font-semibold">Some AWS accounts could not be queried</p>
                    <ul className="mt-2 space-y-1 text-xs text-muted">
                      {data.errors.map((error) => <li key={error.accountId}>{error.account}: {error.detail}</li>)}
                    </ul>
                  </section>
                ) : null}
                <section className="overflow-hidden rounded border border-outline bg-white">
                  <div className="border-b border-outline px-4 py-3">
                    <h2 className="text-sm font-semibold text-ink">Amazon S3 buckets</h2>
                    <p className="mt-1 text-xs text-muted">Bucket objects and object contents are never requested or displayed.</p>
                  </div>
                  {data.items.length === 0 ? (
                    <p className="p-4 text-sm text-muted">No S3 buckets found. Configure an AWS account role with `s3:ListAllMyBuckets`, then ensure the API and worker have valid AWS SSO credentials.</p>
                  ) : (
                    <table className="w-full text-left text-sm">
                      <thead><tr className="border-b border-outline text-[11px] font-bold uppercase text-muted"><th className="p-3">Bucket</th><th className="p-3">AWS account</th><th className="p-3">Created</th></tr></thead>
                      <tbody>{data.items.map((bucket) => <tr key={`${bucket.accountId}:${bucket.name}`} className="border-b border-outline last:border-0"><td className="p-3 font-mono text-xs text-ink">{bucket.name}</td><td className="p-3">{bucket.account}</td><td className="p-3 text-muted">{bucket.createdAt ? new Date(bucket.createdAt).toLocaleString() : "—"}</td></tr>)}</tbody>
                    </table>
                  )}
                </section>
              </>
            )}
          </QueryState>
        </div>
      </main>
    </>
  );
}
