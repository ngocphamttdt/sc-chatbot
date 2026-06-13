import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { createTenantUser, deleteTenantUser, listTenantUsers, updateTenantUserRole } from "../api";
import type { TenantUser } from "../types";

const ROLE_LABELS: Record<string, string> = {
  manager: "Quản lý",
  editor: "Biên tập viên",
  viewer: "Chỉ xem",
};

const ROLE_STYLES: Record<string, string> = {
  manager: "bg-emerald-100 text-emerald-700 border-emerald-200",
  editor: "bg-blue-100 text-blue-700 border-blue-200",
  viewer: "bg-slate-100 text-slate-600 border-slate-200",
};

function formatTime(ts: number) {
  return new Date(ts * 1000).toLocaleString("vi-VN");
}

type Form = { email: string; password: string; role: string };
const emptyForm = (): Form => ({ email: "", password: "", role: "viewer" });

export default function TenantUsers() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const [users, setUsers] = useState<TenantUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState<Form>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<TenantUser | null>(null);
  const [editRole, setEditRole] = useState("");

  const refresh = () => {
    if (!tenantId) return;
    setLoading(true);
    listTenantUsers(tenantId)
      .then(setUsers)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, [tenantId]);

  const openCreate = () => { setForm(emptyForm()); setFormError(null); setModal(true); };

  const submit = async () => {
    if (!tenantId || !form.email.trim() || !form.password.trim()) {
      setFormError("Vui lòng điền đầy đủ email và mật khẩu.");
      return;
    }
    setSaving(true); setFormError(null);
    try {
      await createTenantUser(tenantId, form.email.trim(), form.password, form.role);
      setModal(false);
      refresh();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const openEdit = (u: TenantUser) => { setEditingUser(u); setEditRole(u.role); };

  const saveRole = async () => {
    if (!tenantId || !editingUser) return;
    try {
      await updateTenantUserRole(tenantId, editingUser.id, editRole);
      setEditingUser(null);
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const remove = async (u: TenantUser) => {
    if (!tenantId || !confirm(`Xóa tài khoản ${u.email}?`)) return;
    try {
      await deleteTenantUser(tenantId, u.id);
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Nhân viên Doanh nghiệp</h1>
          <p className="text-sm text-slate-500 mt-1">
            Tenant: <span className="font-mono text-slate-700">{tenantId}</span>
          </p>
        </div>
        <button
          onClick={openCreate}
          className="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition shadow-sm"
        >
          + Thêm nhân viên
        </button>
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-slate-600 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-3">Email</th>
              <th className="text-left px-4 py-3">Role</th>
              <th className="text-left px-4 py-3">Ngày tạo</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-400">Đang tải…</td></tr>
            )}
            {!loading && users.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-400">Chưa có nhân viên nào.</td></tr>
            )}
            {users.map((u) => (
              <tr key={u.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-slate-900">{u.email}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded border font-medium ${ROLE_STYLES[u.role] ?? "bg-gray-100 text-gray-600"}`}>
                    {ROLE_LABELS[u.role] ?? u.role}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-500">{formatTime(u.created_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-3">
                    <button onClick={() => openEdit(u)} className="text-sm text-emerald-600 hover:underline">Đổi role</button>
                    <button onClick={() => remove(u)} className="text-sm text-red-500 hover:underline">Xóa</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create modal */}
      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h2 className="text-lg font-semibold mb-5">Thêm nhân viên</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="nhanvien@company.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Mật khẩu</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="viewer">Chỉ xem</option>
                  <option value="editor">Biên tập viên</option>
                  <option value="manager">Quản lý</option>
                </select>
              </div>
              {formError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{formError}</div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setModal(false)} className="px-4 py-2 rounded border border-gray-300 text-sm text-slate-600 hover:bg-gray-50">Hủy</button>
              <button onClick={submit} disabled={saving} className="px-4 py-2 rounded bg-emerald-600 text-white text-sm hover:bg-emerald-700 disabled:opacity-50 transition">
                {saving ? "Đang tạo…" : "Tạo tài khoản"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit role modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm mx-4 p-6">
            <h2 className="text-lg font-semibold mb-1">Đổi Role</h2>
            <p className="text-sm text-slate-500 mb-5">{editingUser.email}</p>
            <select
              value={editRole}
              onChange={(e) => setEditRole(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="viewer">Chỉ xem</option>
              <option value="editor">Biên tập viên</option>
              <option value="manager">Quản lý</option>
            </select>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setEditingUser(null)} className="px-4 py-2 rounded border border-gray-300 text-sm text-slate-600 hover:bg-gray-50">Hủy</button>
              <button onClick={saveRole} className="px-4 py-2 rounded bg-emerald-600 text-white text-sm hover:bg-emerald-700 transition">Lưu</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
