"use client";

import { useEffect, useId, useSyncExternalStore, type ReactNode } from "react";
import { createPortal } from "react-dom";

const SIZE: Record<"md" | "lg" | "xl", string> = {
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-3xl",
};

export const adminInputClass =
  "h-9 w-full rounded border border-outline bg-white px-3 text-sm text-ink outline-none focus:border-action focus:ring-1 focus:ring-action";

export const adminSelectClass = `${adminInputClass} appearance-none`;

export const adminTextareaClass =
  "w-full rounded border border-outline bg-white px-3 py-2 font-mono text-xs text-ink outline-none focus:border-action focus:ring-1 focus:ring-action";

export function AdminDialog({
  title,
  hint,
  size = "lg",
  onClose,
  footer,
  children,
}: {
  title: string;
  hint?: string;
  size?: "md" | "lg" | "xl";
  onClose: () => void;
  footer?: ReactNode;
  children: ReactNode;
}) {
  const titleId = useId();
  useOverlay(onClose);

  return (
    <OverlayPortal>
    <div className="fixed inset-0 z-[70] flex items-start justify-center overflow-y-auto p-4 sm:items-center">
      <button type="button" className="fixed inset-0 bg-black/45" aria-label="Close dialog" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={`relative z-10 my-8 w-full ${SIZE[size]} overflow-hidden rounded-lg border border-outline bg-white shadow-2xl`}
      >
        <header className="flex items-start justify-between gap-4 border-b border-outline bg-surface-low px-5 py-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted">Configuration</p>
            <h2 id={titleId} className="mt-1 text-lg font-semibold text-ink">
              {title}
            </h2>
            {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
          </div>
          <button
            type="button"
            className="rounded p-1 text-muted hover:bg-white hover:text-ink"
            aria-label="Close"
            onClick={onClose}
          >
            <CloseIcon />
          </button>
        </header>
        <div className="max-h-[min(70vh,640px)] overflow-y-auto px-5 py-5">{children}</div>
        {footer ? <footer className="flex justify-end gap-2 border-t border-outline bg-surface-low px-5 py-3">{footer}</footer> : null}
      </div>
    </div>
    </OverlayPortal>
  );
}

export function AdminDrawer({
  title,
  hint,
  onClose,
  children,
}: {
  title: string;
  hint?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const titleId = useId();
  useOverlay(onClose);

  return (
    <OverlayPortal>
    <div className="fixed inset-0 z-[70] flex justify-end">
      <button type="button" className="absolute inset-0 bg-black/45" aria-label="Close drawer" onClick={onClose} />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative z-10 flex h-full w-full max-w-xl flex-col border-l border-outline bg-white shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-outline bg-surface-low px-5 py-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted">Details</p>
            <h2 id={titleId} className="mt-1 text-lg font-semibold text-ink">
              {title}
            </h2>
            {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
          </div>
          <button
            type="button"
            className="rounded p-1 text-muted hover:bg-white hover:text-ink"
            aria-label="Close"
            onClick={onClose}
          >
            <CloseIcon />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-5">{children}</div>
      </aside>
    </div>
    </OverlayPortal>
  );
}

export function AdminTabs<T extends string>({
  items,
  value,
  labels,
  onChange,
  ariaLabel = "Administration sections",
}: {
  items: readonly T[];
  value: T;
  labels: Record<T, string>;
  onChange: (value: T) => void;
  ariaLabel?: string;
}) {
  return (
    <div className="border-b border-outline bg-white">
      <nav className="flex gap-6 overflow-x-auto px-4" aria-label={ariaLabel}>
        {items.map((item) => {
          const active = item === value;
          return (
            <button
              key={item}
              type="button"
              aria-current={active ? "page" : undefined}
              className={
                active
                  ? "shrink-0 border-b-2 border-action py-3 text-[11px] font-bold uppercase tracking-wide text-action"
                  : "shrink-0 border-b-2 border-transparent py-3 text-[11px] font-bold uppercase tracking-wide text-muted hover:text-ink"
              }
              onClick={() => onChange(item)}
            >
              {labels[item]}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

export function AdminToast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  const failed = /fail|unable|error|denied/i.test(message);
  useEffect(() => {
    const timer = window.setTimeout(onDismiss, 4500);
    return () => window.clearTimeout(timer);
  }, [message, onDismiss]);

  return (
    <div
      role="status"
      className={
        failed
          ? "fixed right-6 top-20 z-[80] flex max-w-md items-start gap-3 rounded-lg border border-critical/30 bg-white px-4 py-3 shadow-lg"
          : "fixed right-6 top-20 z-[80] flex max-w-md items-start gap-3 rounded-lg border border-healthy/30 bg-white px-4 py-3 shadow-lg"
      }
    >
      <span
        className={
          failed
            ? "mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-critical text-[10px] font-bold text-white"
            : "mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-healthy text-[10px] font-bold text-white"
        }
      >
        {failed ? "!" : "✓"}
      </span>
      <p className="text-sm text-ink">{message}</p>
      <button type="button" className="ml-2 text-muted hover:text-ink" aria-label="Dismiss" onClick={onDismiss}>
        <CloseIcon />
      </button>
    </div>
  );
}

export function WizardStepper({ steps, current }: { steps: readonly string[]; current: number }) {
  return (
    <ol className="mb-6 grid grid-cols-5 gap-2">
      {steps.map((label, index) => {
        const step = index + 1;
        const done = step < current;
        const active = step === current;
        return (
          <li key={label} className="flex flex-col items-center text-center">
            <span
              className={
                active
                  ? "flex h-7 w-7 items-center justify-center rounded-full bg-action text-xs font-bold text-white"
                  : done
                    ? "flex h-7 w-7 items-center justify-center rounded-full bg-healthy text-xs font-bold text-white"
                    : "flex h-7 w-7 items-center justify-center rounded-full border border-outline text-xs font-bold text-muted"
              }
            >
              {done ? "✓" : step}
            </span>
            <span
              className={
                active
                  ? "mt-2 text-[10px] font-bold uppercase tracking-wide text-action"
                  : "mt-2 text-[10px] font-bold uppercase tracking-wide text-muted"
              }
            >
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function ChoiceCard({
  title,
  description,
  selected,
  onSelect,
}: {
  title: string;
  description: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={
        selected
          ? "rounded-lg border-2 border-action bg-action/5 px-4 py-4 text-left"
          : "rounded-lg border border-outline bg-white px-4 py-4 text-left hover:border-action/40"
      }
    >
      <p className="text-sm font-semibold text-ink">{title}</p>
      <p className="mt-1 text-xs text-muted">{description}</p>
    </button>
  );
}

export function AdminField({
  label,
  value,
  onChange,
  type = "text",
  className,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  className?: string;
  autoComplete?: string;
}) {
  return (
    <label className={`block space-y-1 ${className || ""}`}>
      <span className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</span>
      <input
        type={type}
        className={adminInputClass}
        value={value}
        autoComplete={autoComplete}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

export function AdminSelect({
  label,
  value,
  onChange,
  children,
  className,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`block space-y-1 ${className || ""}`}>
      <span className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</span>
      <select className={adminSelectClass} value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
    </label>
  );
}

export function AdminTextarea({
  label,
  value,
  onChange,
  rows = 4,
  className,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  className?: string;
}) {
  return (
    <label className={`block space-y-1 ${className || ""}`}>
      <span className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</span>
      <textarea className={adminTextareaClass} rows={rows} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

export function GhostButton({
  children,
  onClick,
  disabled,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      className="rounded border border-outline bg-white px-3 py-1.5 text-xs font-semibold text-ink hover:bg-surface-low disabled:opacity-40"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export function PrimaryButton({
  children,
  onClick,
  disabled,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white hover:bg-action/90 disabled:opacity-40"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export function EmptyCatalog({
  title,
  description,
  action,
  onClick,
}: {
  title: string;
  description: string;
  action: string;
  onClick: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-dashed border-outline text-lg text-muted">
        +
      </div>
      <p className="text-sm font-semibold text-ink">{title}</p>
      <p className="mt-1 max-w-md text-xs text-muted">{description}</p>
      <button type="button" className="mt-4 rounded bg-action px-4 py-2 text-xs font-semibold text-white" onClick={onClick}>
        {action}
      </button>
    </div>
  );
}

export function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 break-all text-sm text-ink">{value}</p>
    </div>
  );
}

function useOverlay(onClose: () => void) {
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);
}

function OverlayPortal({ children }: { children: ReactNode }) {
  const mounted = useSyncExternalStore(subscribeToClientMount, getClientSnapshot, getServerSnapshot);

  return mounted ? createPortal(children, document.body) : null;
}

function subscribeToClientMount() {
  return () => {};
}

function getClientSnapshot() {
  return true;
}

function getServerSnapshot() {
  return false;
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden>
      <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
