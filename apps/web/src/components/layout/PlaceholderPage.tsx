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
            Overview, Environments, Secrets, Certificates, and the remaining console catalogs are
            implemented. {title} will reuse the same CloudOps layout if this route is reached.
          </p>
        </div>
      </main>
    </>
  );
}
