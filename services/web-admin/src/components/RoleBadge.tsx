import type { Role, RoleColor } from "../types";

export const COLOR_MAP: Record<RoleColor, string> = {
  emerald: "bg-emerald-100 text-emerald-700 border-emerald-200",
  blue: "bg-blue-100 text-blue-700 border-blue-200",
  purple: "bg-purple-100 text-purple-700 border-purple-200",
  amber: "bg-amber-100 text-amber-700 border-amber-200",
  slate: "bg-slate-100 text-slate-700 border-slate-200",
  rose: "bg-rose-100 text-rose-700 border-rose-200",
};

export default function RoleBadge({ role }: { role: Role }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-medium ${COLOR_MAP[role.color]}`}>
      {role.name}
    </span>
  );
}
