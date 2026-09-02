import { PageHeader } from "@/components/layout/PageHeader";
import { NAV_ITEMS } from "@/lib/navigation";

export function PlaceholderPage({ section }: { section: string }) {
  const item = NAV_ITEMS.find((entry) => entry.href === `/${section}`);
  const title = item?.label ?? section;

  return (
    <>
      <PageHeader title={title} subtitle="This console area is not implemented yet." />
      <main className="flex-1 p-6">
        <div className="rounded border border-outline bg-white p-6">
          <p className="text-sm text-muted">
            Overview, Environment Details, and Secrets Management are implemented. {title} will reuse
            the same CloudOps layout, environment model, and production/non-production treatment.
          </p>
        </div>
      </main>
    </>
  );
}
