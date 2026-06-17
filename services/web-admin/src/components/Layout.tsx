import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import type { Permission } from "../types";
import {
  BuildingIcon,
  ChatIcon,
  DashboardIcon,
  DocsIcon,
  LogoIcon,
  PromptIcon,
  SettingsIcon,
  ShieldIcon,
  UsersIcon,
} from "./Icons";

type NavItem = {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  permission?: Permission;
};

const NAV_MAIN: NavItem[] = [
  { to: "/stats",         label: "Dashboard",      icon: DashboardIcon, permission: "stats.read" },
  { to: "/documents",     label: "Knowledge base",  icon: DocsIcon,      permission: "documents.read" },
  { to: "/prompt",        label: "System prompt",   icon: PromptIcon,    permission: "prompt.read" },
  { to: "/conversations", label: "Hội thoại",       icon: ChatIcon,      permission: "conversations.read" },
];

// Chỉ admin (SC-Bot staff) mới thấy section này
const NAV_ADMIN: NavItem[] = [
  { to: "/tenants", label: "Doanh nghiệp", icon: BuildingIcon },
  { to: "/users",   label: "Nhân viên",    icon: UsersIcon },
  { to: "/roles",   label: "Roles",    icon: ShieldIcon },
  { to: "/settings", label: "Cấu hình", icon: SettingsIcon },
];

const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super Admin",
  support: "Support",
  manager: "Quản lý",
  editor: "Biên tập viên",
  viewer: "Chỉ xem",
};

function navLinkClass({ isActive }: { isActive: boolean }) {
  return `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition ${
    isActive ? "bg-emerald-50 text-emerald-700 font-medium" : "text-slate-600 hover:bg-gray-100"
  }`;
}

export default function Layout() {
  const { logout, displayName, role, isAdmin, isSuperAdmin, tenantName, can } = useAuth();
  const nav = useNavigate();

  const onLogout = () => { logout(); nav("/login", { replace: true }); };

  // Lọc NAV_MAIN: admin thấy hết, tenant user chỉ thấy item có permission
  const visibleMain = NAV_MAIN.filter((n) => !n.permission || can(n.permission));

  return (
    <div className="min-h-screen flex bg-gray-50 text-slate-900">
      <aside className="w-60 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-5 py-4 flex items-center gap-2 border-b border-gray-100">
          <LogoIcon className="text-emerald-600" />
          <div className="min-w-0">
            <span className="font-semibold text-slate-900">SC Chatbot</span>
            {!isSuperAdmin && tenantName && (
              <div className="text-xs text-slate-400 truncate">{tenantName}</div>
            )}
          </div>
        </div>

        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {visibleMain.map((n) => {
            const Icon = n.icon;
            return (
              <NavLink key={n.to} to={n.to} className={navLinkClass}>
                <Icon /><span>{n.label}</span>
              </NavLink>
            );
          })}

          {/* Phân quyền section: CHỈ admin SC-Bot mới thấy */}
          {isAdmin && (
            <>
              <div className="pt-3 pb-1 px-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Phân quyền
                </span>
              </div>
              {NAV_ADMIN.map((n) => {
                const Icon = n.icon;
                return (
                  <NavLink key={n.to} to={n.to} className={navLinkClass}>
                    <Icon /><span>{n.label}</span>
                  </NavLink>
                );
              })}
            </>
          )}
        </nav>

        <div className="border-t border-gray-100 px-3 py-3">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-medium text-sm shrink-0">
              {(displayName?.[0] ?? "A").toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-900 truncate">{displayName ?? "Admin"}</div>
              <div className="text-xs text-slate-400 truncate">{ROLE_LABELS[role ?? ""] ?? role ?? "Administrator"}</div>
            </div>
          </div>
          <button
            onClick={onLogout}
            className="mt-1 w-full px-3 py-1.5 rounded-md border border-gray-200 text-sm text-slate-600 hover:bg-gray-50 transition"
          >
            Đăng xuất
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
