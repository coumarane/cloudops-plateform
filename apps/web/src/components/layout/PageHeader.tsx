import { Bell, CircleHelp } from "lucide-react";

export function PageHeader({
  title,
  subtitle,
  meta,
}: {
  title: string;
  subtitle?: string;
  meta?: string;
}) {
  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-outline bg-canvas px-6">
      <div>
        <h1 className="text-lg font-semibold text-ink">{title}</h1>
        {subtitle ? <p className="text-xs text-muted">{subtitle}</p> : null}
      </div>
      <div className="flex items-center gap-4 text-muted">
        {meta ? <span className="font-mono text-xs">{meta}</span> : null}
        <Bell className="h-4 w-4" aria-hidden />
        <CircleHelp className="h-4 w-4" aria-hidden />
      </div>
    </header>
  );
}
