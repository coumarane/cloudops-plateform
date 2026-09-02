export type NavItem = {
  href: string;
  label: string;
  icon:
    | "overview"
    | "infrastructure"
    | "clusters"
    | "environments"
    | "applications"
    | "secrets"
    | "certificates"
    | "health"
    | "deployments"
    | "pipelines"
    | "github"
    | "jobs"
    | "alerts"
    | "audit"
    | "administration";
};

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Overview", icon: "overview" },
  { href: "/infrastructure", label: "Infrastructure", icon: "infrastructure" },
  { href: "/clusters", label: "Clusters", icon: "clusters" },
  { href: "/environments", label: "Environments", icon: "environments" },
  { href: "/applications", label: "Applications", icon: "applications" },
  { href: "/secrets", label: "Secrets", icon: "secrets" },
  { href: "/certificates", label: "Certificates", icon: "certificates" },
  { href: "/health-checks", label: "Health Checks", icon: "health" },
  { href: "/deployments", label: "Deployments", icon: "deployments" },
  { href: "/pipelines", label: "Pipelines", icon: "pipelines" },
  { href: "/github", label: "GitHub", icon: "github" },
  { href: "/jobs", label: "Jobs", icon: "jobs" },
  { href: "/alerts", label: "Alerts", icon: "alerts" },
  { href: "/audit", label: "Audit", icon: "audit" },
  { href: "/administration", label: "Administration", icon: "administration" },
];

const IMPLEMENTED_HREFS = new Set(["/", "/environments", "/secrets", "/certificates"]);

export const PLACEHOLDER_SECTIONS = NAV_ITEMS.filter((item) => !IMPLEMENTED_HREFS.has(item.href)).map(
  (item) => item.href.slice(1),
);

export function isPlaceholderSection(section: string): boolean {
  return PLACEHOLDER_SECTIONS.includes(section);
}
