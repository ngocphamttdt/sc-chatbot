import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  createTenantUser,
  deleteTenantUser,
  listTenantUsers,
  listTenants,
  listRoles,
  updateTenantUserRole,
} from "../api";
import type { Role, RoleColor, Tenant, TenantUser } from "../types";

const COLOR_CLASSES: Record<RoleColor, string> = {
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
  blue:    "bg-blue-50 text-blue-700 border-blue-200",
  purple:  "bg-purple-50 text-purple-700 border-purple-200",
  amber:   "bg-amber-50 text-amber-700 border-amber-200",
  slate:   "bg-slate-50 text-slate-600 border-slate-200",
  rose:    "bg-rose-50 text-rose-700 border-rose-200",
};

type CreateForm = { email: string; password: string; confirmPassword: string; role: string };
const emptyForm = (): CreateForm => ({ email: "", password: "", confirmPassword: "", role: "viewer" });

export default function Users() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [roles, setRoles] = useState<Role[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [users, setUsers] = useState<TenantUser[]>([]);
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [createModal, setCreateModal] = useState(false);
  const [form, setForm] = useState<CreateForm>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    listRoles().then(setRoles).catch(() => {});
  }, []);

  useEffect(() => {
    listTenants()
      .then((ts) => {
        setTenants(ts);
        const param = searchParams.get("tenant");
        const pick = param && ts.find((t) => t.tenant_id === param)
          ? param
          : ts[0]?.tenant_id ?? "";
        setSelectedId(pick);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoadingTenants(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadUsers = (tenantId: string) => {
    if (!tenantId) return;
    setLoadingUsers(true);
    setError(null);
    listTenantUsers(tenantId)
      .then(setUsers)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoadingUsers(false));
  };

  useEffect(() => {
    loadUsers(selectedId);
  }, [selectedId]);

  const handleTenantChange = (id: string) => {
    setSelectedId(id);
    setSearchParams({ tenant: id });
  };

  const openCreate = () => {
    setForm(emptyForm());
    setFormError(null);
    setCreateModal(true);
  };

  const submitCreate = async () => {
    if (!form.email.trim() || !form.password.trim()) {
      setFormError("Vui lòng điền username và mật khẩu.");
      return;
    }
    if (form.password !== form.confirmPassword) {
      setFormError("Mật khẩu nhập lại không khớp.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await createTenantUser(selectedId, form.email.trim(), form.password, form.role);
      setCreateModal(false);
      loadUsers(selectedId);
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm("Xóa nhân viên này?")) return;
    try {
      await deleteTenantUser(selectedId, userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const handleRoleChange = async (userId: string, roleId: string) => {
    try {
      await updateTenantUserRole(selectedId, userId, roleId);
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role: roleId } : u));
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const roleById = (id: string): Role | undefined => roles.find((r) => r.id === id);

  const selectedTenant = tenants.find((t) => t.tenant_id === selectedId);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Nhân viên</h1>
          <p className="text-sm text-slate-500 mt-1">Quản lý nhân viên theo doanh nghiệp</p>
        </div>
        {selectedId && (
          <button
            onClick={openCreate}
            className="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition shadow-sm"
          >
            + Thêm nhân viên
          </button>
        )}
      </div>

      {/* Tenant selector */}
      <div className="mb-5 flex items-center gap-3">
        <span className="text-sm font-medium text-slate-600">Doanh nghiệp:</span>
        {loadingTenants ? (
          <span className="text-sm text-slate-400">Đang tải…</span>
        ) : tenants.length === 0 ? (
          <span className="text-sm text-slate-400">Chưa có doanh nghiệp nào.</span>
        ) : (
          <select
            value={selectedId}
            onChange={(e) => handleTenantChange(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {tenants.map((t) => (
              <option key={t.tenant_id} value={t.tenant_id}>
                {t.name} — {t.tenant_id}
              </option>
            ))}
          </select>
        )}
        {selectedTenant && (
          <span className="ml-auto text-xs text-slate-400">
            {users.length} nhân viên
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-slate-600 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-4 py-3">User</th>
              <th className="text-left px-4 py-3">Role</th>
              <th className="text-left px-4 py-3">Ngày tạo</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {loadingUsers && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-slate-400">
                  Đang tải…
                </td>
              </tr>
            )}
            {!loadingUsers && users.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-slate-400">
                  Chưa có nhân viên nào trong doanh nghiệp này.
                </td>
              </tr>
            )}
            {users.map((u) => {
              const role = roleById(u.role);
              const colorClass = role ? COLOR_CLASSES[role.color] : COLOR_CLASSES.slate;
              return (
                <tr key={u.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{u.email}</td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      onChange={(e) => handleRoleChange(u.id, e.target.value)}
                      className={`text-xs font-medium border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-emerald-500 ${colorClass}`}
                    >
                      {roles.map((r) => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {new Date(u.created_at * 1000).toLocaleDateString("vi-VN")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(u.id)}
                      className="text-xs text-red-500 hover:text-red-700 hover:underline"
                    >
                      Xóa
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {/* Create user modal */}
      {createModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h2 className="text-lg font-semibold mb-1">Thêm nhân viên</h2>
            <p className="text-sm text-slate-500 mb-5">
              Doanh nghiệp:{" "}
              <span className="font-medium text-slate-800">{selectedTenant?.name}</span>
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Username <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="VD: john.doe"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Mật khẩu <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                    className="w-full border border-gray-300 rounded px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <button type="button" onClick={() => setShowPassword((v) => !v)}
                    className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 hover:text-slate-600" tabIndex={-1}>
                    {showPassword ? (
                      <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>
                      </svg>
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Nhập lại mật khẩu <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showConfirm ? "text" : "password"}
                    value={form.confirmPassword}
                    onChange={(e) => setForm((f) => ({ ...f, confirmPassword: e.target.value }))}
                    className={`w-full border rounded px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
                      form.confirmPassword && form.confirmPassword !== form.password
                        ? "border-red-400"
                        : "border-gray-300"
                    }`}
                  />
                  <button type="button" onClick={() => setShowConfirm((v) => !v)}
                    className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 hover:text-slate-600" tabIndex={-1}>
                    {showConfirm ? (
                      <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>
                      </svg>
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                      </svg>
                    )}
                  </button>
                </div>
                {form.confirmPassword && form.confirmPassword !== form.password && (
                  <p className="text-xs text-red-500 mt-1">Mật khẩu không khớp</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
                </select>
              </div>

              {formError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                  {formError}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setCreateModal(false)}
                className="px-4 py-2 rounded border border-gray-300 text-sm text-slate-600 hover:bg-gray-50"
              >
                Hủy
              </button>
              <button
                onClick={submitCreate}
                disabled={saving}
                className="px-4 py-2 rounded bg-emerald-600 text-white text-sm hover:bg-emerald-700 disabled:opacity-50 transition"
              >
                {saving ? "Đang thêm…" : "Thêm nhân viên"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
