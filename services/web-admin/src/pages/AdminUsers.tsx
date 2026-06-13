import { useEffect, useState } from "react";
import { createAdminUser, deleteAdminUser, listAdminUsers } from "../api";
import { useAuth } from "../auth";
import type { AdminUser } from "../types";

const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super Admin",
  support: "Support",
};

const ROLE_STYLES: Record<string, string> = {
  super_admin: "bg-emerald-100 text-emerald-700 border-emerald-200",
  support: "bg-blue-100 text-blue-700 border-blue-200",
};

function formatTime(ts: number) {
  return new Date(ts * 1000).toLocaleString("vi-VN");
}

type Form = { email: string; password: string; role: string };
const emptyForm = (): Form => ({ email: "", password: "", role: "support" });

export default function AdminUsers() {
  const { isSuperAdmin } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState<Form>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const refresh = () => {
    setLoading(true);
    listAdminUsers()
      .then(setUsers)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  const openModal = () => { setForm(emptyForm()); setFormError(null); setModal(true); };

  const submit = async () => {
    if (!form.email.trim() || !form.password.trim()) {
      setFormError("Vui lòng điền đầy đủ email và mật khẩu.");
      return;
    }
    setSaving(true); setFormError(null);
    try {
      await createAdminUser(form.email.trim(), form.password, form.role);
      setModal(false);
      refresh();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (user: AdminUser) => {
    if (!confirm(`Xóa tài khoản ${user.email}?`)) return;
    try {
      await deleteAdminUser(user.id);
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Nhân viên Web-Admin</h1>
          <p className="text-sm text-slate-500 mt-1">Tài khoản quản trị nội bộ của nền tảng</p>
        </div>
        {isSuperAdmin && (
          <button
            onClick={openModal}
            className="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition shadow-sm"
          >
            + Thêm nhân viên
          </button>
        )}
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
                <td className="px-4 py-3 text-right">
                  {isSuperAdmin && (
                    <button onClick={() => remove(u)} className="text-sm text-red-500 hover:underline">
                      Xóa
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h2 className="text-lg font-semibold mb-5">Thêm nhân viên mới</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="staff@company.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Mật khẩu</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="Tối thiểu 8 ký tự"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="support">Support — xem tất cả tenant</option>
                  <option value="super_admin">Super Admin — toàn quyền</option>
                </select>
              </div>
              {formError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                  {formError}
                </div>
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
    </div>
  );
}
