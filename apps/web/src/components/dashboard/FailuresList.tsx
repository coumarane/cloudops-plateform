import Link from "next/link";
import { EnvBadge } from "@/components/status/EnvBadge";
import type { RecentFailure } from "@/lib/types";

const KIND_LABEL: Record<RecentFailure["kind"], string> = {
  deployment: "Deploy",
  github: "GitHub",
  pipeline: "Pipe",
};

export function FailuresList({ failures }: { failures: RecentFailure[] }) {
  return (
    <section className="rounded border border-outline bg-white">
      <div className="border-b border-outline p-4">
        <h2 className="text-lg font-semibold text-ink">Recent Failures</h2>
      </div>
      {failures.length === 0 ? (
        <p className="p-4 text-sm text-muted">No failures in the current filter.</p>
      ) : (
        <table className="w-full border-collapse text-left text-[13px]">
          <thead>
            <tr className="border-b border-outline bg-canvas">
              <th className="p-2 text-[11px] font-bold uppercase tracking-wide text-muted">Name</th>
              <th className="p-2 text-[11px] font-bold uppercase tracking-wide text-muted">Region/Env</th>
              <th className="p-2 text-right text-[11px] font-bold uppercase tracking-wide text-muted">Time</th>
            </tr>
          </thead>
          <tbody>
            {failures.map((failure) => (
              <tr key={failure.id} className="border-b border-outline last:border-b-0">
                <td className="p-2">
                  <Link href={failure.href} className="font-mono text-xs text-critical hover:underline">
                    {KIND_LABEL[failure.kind]}: {failure.name}
                  </Link>
                </td>
                <td className="p-2">
                  <div className="flex items-center gap-1">
                    <span className="text-[10px] text-muted">{failure.region}</span>
                    <EnvBadge environment={failure.environment} />
                  </div>
                </td>
                <td className="p-2 text-right text-xs text-muted">{failure.age}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
