import {
  LayoutDashboard,
  FileSearch,
  TrendingUp,
  ListChecks,
  Sparkles,
  Workflow,
  FilePlus,
  ShieldCheck,
  Settings,
  Scale,
  type LucideIcon,
} from "lucide-react";
import type { Role } from "./types";

export const ALL_ROLES: Role[] = [
  "cfo",
  "supply_chain",
  "claims_finance",
  "sales_rsm",
  "cnf_agent",
  "admin",
];

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  roles: "all" | Role[];
}

/**
 * Role visibility follows the RBAC matrix in the project brief
 * (CFO / Supply Chain / Claims Finance / Sales RSM / CNF Agent / Admin).
 * Informational pages (Agent Workflow, Why This Exists) and the personal
 * My Claims page are open to every authenticated role.
 */
export const NAV: NavItem[] = [
  { label: "Recovery", href: "/dashboard", icon: LayoutDashboard, roles: "all" },
  { label: "Recovery Register", href: "/opportunities", icon: ListChecks, roles: ["claims_finance", "cfo", "supply_chain", "admin"] },
  { label: "Check a Claim", href: "/gatekeeper", icon: ShieldCheck, roles: "all" },
  { label: "Recovery List", href: "/claims-findings", icon: FileSearch, roles: ["claims_finance", "cfo", "admin"] },
  { label: "Scheme Returns", href: "/quarter-spike", icon: TrendingUp, roles: ["cfo", "supply_chain", "admin"] },
  { label: "Allocation, FEFO, Cap", href: "/supply-check", icon: Scale, roles: ["supply_chain", "cfo", "admin"] },
  { label: "Ask AI", href: "/ask", icon: Sparkles, roles: ["cfo", "supply_chain", "claims_finance", "admin"] },
  { label: "File a Claim", href: "/my-claims", icon: FilePlus, roles: "all" },
  { label: "Review Queue", href: "/auditor", icon: ShieldCheck, roles: ["claims_finance", "cfo", "admin"] },
  { label: "Agents", href: "/agents", icon: Workflow, roles: "all" },
  { label: "Admin", href: "/admin", icon: Settings, roles: ["admin"] },
];

export function navForRole(role: Role | undefined): NavItem[] {
  if (!role) return [];
  return NAV.filter((n) => n.roles === "all" || n.roles.includes(role));
}

export const PAGE_TITLES: Record<string, string> = {
  "/": "Sign In",
  ...Object.fromEntries(NAV.map((n) => [n.href, n.label])),
};

/** Roles that may act as auditors (approve/reject claims). */
export const AUDITOR_ROLES: Role[] = ["claims_finance", "cfo", "admin"];

/** Where each role lands after sign-in: a screen its role may open. */
export function homeFor(role: Role | undefined): string {
  if (role === "supply_chain") return "/supply-check";
  if (role === "sales_rsm" || role === "cnf_agent") return "/gatekeeper";
  return "/dashboard";
}
