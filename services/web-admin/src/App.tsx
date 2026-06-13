import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import Layout from "./components/Layout";
import Protected from "./components/Protected";
import { useAuth } from "./auth";
import type { Permission } from "./types";
import Conversations from "./pages/Conversations";
import Documents from "./pages/Documents";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import Prompt from "./pages/Prompt";
import Settings from "./pages/Settings";
import Roles from "./pages/Roles";
import Stats from "./pages/Stats";
import TenantUsers from "./pages/TenantUsers";
import Tenants from "./pages/Tenants";
import Users from "./pages/Users";

// Redirect to the first route the user has permission for
function SmartRedirect() {
  const { isAdmin, can } = useAuth();
  if (isAdmin) return <Navigate to="/stats" replace />;
  const ordered: { path: string; permission: Permission }[] = [
    { path: "/stats",         permission: "stats.read" },
    { path: "/conversations", permission: "conversations.read" },
    { path: "/documents",     permission: "documents.read" },
    { path: "/prompt",        permission: "prompt.read" },
  ];
  const first = ordered.find((r) => can(r.permission));
  return <Navigate to={first?.path ?? "/not-found"} replace />;
}

// Guard for permission-based routes — redirects to /not-found if lacking access
function RequirePermission({ permission, children }: { permission: Permission; children: ReactNode }) {
  const { can } = useAuth();
  if (!can(permission)) return <Navigate to="/not-found" replace />;
  return <>{children}</>;
}

// Guard for admin-only routes
function RequireAdmin({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth();
  if (!isAdmin) return <Navigate to="/not-found" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<SmartRedirect />} />
        <Route path="stats"         element={<RequirePermission permission="stats.read"><Stats /></RequirePermission>} />
        <Route path="documents"     element={<RequirePermission permission="documents.read"><Documents /></RequirePermission>} />
        <Route path="prompt"        element={<RequirePermission permission="prompt.read"><Prompt /></RequirePermission>} />
        <Route path="conversations" element={<RequirePermission permission="conversations.read"><Conversations /></RequirePermission>} />
        <Route path="tenants"             element={<RequireAdmin><Tenants /></RequireAdmin>} />
        <Route path="tenants/:tenantId/users" element={<RequireAdmin><TenantUsers /></RequireAdmin>} />
        <Route path="users"               element={<RequireAdmin><Users /></RequireAdmin>} />
        <Route path="roles"               element={<RequireAdmin><Roles /></RequireAdmin>} />
        <Route path="not-found" element={<NotFound />} />
      </Route>
      <Route path="*" element={<Navigate to="/not-found" replace />} />
    </Routes>
  );
}
