import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import {
  ChatIcon,
  DashboardIcon,
  DocsIcon,
  LogoIcon,
  PromptIcon,
  SettingsIcon,
} from "./Icons";

const NAV = [
  { to: "/stats", label: "Dashboard", icon: DashboardIcon },
  { to: "/documents", label: "Knowledge base", icon: DocsIcon },
  { to: "/prompt", label: "System prompt", icon: PromptIcon },
  { to: "/settings", label: "Cấu hình", icon: SettingsIcon },
  { to: "/conversations", label: "Hội thoại", icon: ChatIcon },
];

export default function Layout() {
  const { logout } = useAuth();
  const nav = useNavigate();

  const onLogout = () => {
    logout();
    nav("/login", { replace: true });
  };

  return (
    <div className="min-h-screen flex bg-gray-50 text-slate-900">
      <aside className="w-60 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-5 py-4 flex items-center gap-2 border-b border-gray-100">
          <LogoIcon className="text-emerald-600" />
          <span className="font-semibold text-slate-900">SC Chatbot</span>
        </div>

        <nav className="flex-1 px-3 py-3 space-y-0.5">
          {NAV.map((n) => {
            const Icon = n.icon;
            return (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition ${
                    isActive
                      ? "bg-emerald-50 text-emerald-700 font-medium"
                      : "text-slate-600 hover:bg-gray-100"
                  }`
                }
              >
                <Icon />
                <span>{n.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-gray-100 px-3 py-3">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-medium text-sm">
              A
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-900 truncate">
                Admin
              </div>
              <div className="text-xs text-slate-400 truncate">Administrator</div>
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
