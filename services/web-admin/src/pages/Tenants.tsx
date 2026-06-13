import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createTenant, listTenants, updateTenant } from "../api";
import type { Tenant } from "../types";

type CreateForm = { tenant_id: string; name: string; industry: string };
type EditForm = { name: string; industry: string };

const emptyCreate = (): CreateForm => ({ tenant_id: "", name: "", industry: "" });

export default function Tenants() {
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [createModal, setCreateModal] = useState(false);
  const [form, setForm] = useState<CreateForm>(emptyCreate());
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [editModal, setEditModal] = useState<Tenant | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({ name: "", industry: "" });
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const refresh = () => {
    setLoading(true);
    listTenants()
      .then(setTenants)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  const openCreate = () => {
    setForm(emptyCreate());
    setFormError(null);
    setCreateModal(true);
  };

  const submitCreate = async () => {
    if (!form.tenant_id.trim() || !form.name.trim()) {
      setFormError("Vui lòng điền đầy đủ Tenant ID và Tên.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await createTenant(form.tenant_id.trim(), form.name.trim(), form.industry.trim() || "general");
      setCreateModal(false);
      refresh();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const openEdit = (t: Tenant) => {
    setEditForm({ name: t.name, industry: t.industry });
    setEditError(null);
    setEditModal(t);
  };

  const submitEdit = async () => {
    if (!editModal || !editForm.name.trim()) {
      setEditError("Tên doanh nghiệp không được để trống.");
      return;
    }
    setEditSaving(true);
    setEditError(null);
    try {
      await updateTenant(editModal.tenant_id, editForm.name.trim(), editForm.industry.trim());
      setEditModal(null);
      refresh();
    } catch (e) {
      setEditError((e as Error).message);
    } finally {
      setEditSaving(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Quản lý Doanh nghiệp</h1>
          <p className="text-sm text-slate-500 mt-1">Tạo và quản lý các tenant trên hệ thống</p>
        </div>
        <button
          onClick={openCreate}
          className="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition shadow-sm"
        >
          + Thêm doanh nghiệp
        </button>
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
              <th className="text-left px-4 py-3">Tên doanh nghiệp</th>
              <th className="text-left px-4 py-3">Tenant ID</th>
              <th className="text-left px-4 py-3">Mô tả</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-slate-400">Đang tải…</td>
              </tr>
            )}
            {!loading && tenants.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-slate-400">Chưa có doanh nghiệp nào.</td>
              </tr>
            )}
            {tenants.map((t) => (
              <tr key={t.tenant_id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-slate-900">{t.name}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-500">{t.tenant_id}</td>
                <td className="px-4 py-3 text-slate-500">{t.industry || "—"}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-3">
                    <button
                      onClick={() => navigate(`/users?tenant=${t.tenant_id}`)}
                      className="text-sm text-slate-600 hover:underline"
                    >
                      Nhân viên
                    </button>
                    <button
                      onClick={() => openEdit(t)}
                      className="text-sm text-emerald-600 hover:underline font-medium"
                    >
                      Sửa
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create modal */}
      {createModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h2 className="text-lg font-semibold mb-5">Thêm doanh nghiệp mới</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Tenant ID <span className="text-red-500">*</span>
                </label>
                <input
                  value={form.tenant_id}
                  onChange={(e) => setForm((f) => ({ ...f, tenant_id: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="VD: beauty-salon-hcm"
                  autoFocus
                />
                <p className="text-xs text-slate-400 mt-1">Chữ thường, gạch nối, không dấu. Không thể thay đổi sau khi tạo.</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Tên doanh nghiệp <span className="text-red-500">*</span>
                </label>
                <input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="VD: Beauty Salon HCM"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Mô tả</label>
                <input
                  value={form.industry}
                  onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="VD: Spa & làm đẹp tại HCM"
                />
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
                {saving ? "Đang tạo…" : "Tạo doanh nghiệp"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {editModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h2 className="text-lg font-semibold mb-1">Chỉnh sửa doanh nghiệp</h2>
            <p className="text-xs text-slate-400 font-mono mb-5">{editModal.tenant_id}</p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Tên doanh nghiệp <span className="text-red-500">*</span>
                </label>
                <input
                  value={editForm.name}
                  onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Mô tả</label>
                <input
                  value={editForm.industry}
                  onChange={(e) => setEditForm((f) => ({ ...f, industry: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="VD: Spa & làm đẹp tại HCM"
                />
              </div>

              {editError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                  {editError}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setEditModal(null)}
                className="px-4 py-2 rounded border border-gray-300 text-sm text-slate-600 hover:bg-gray-50"
              >
                Hủy
              </button>
              <button
                onClick={submitEdit}
                disabled={editSaving}
                className="px-4 py-2 rounded bg-emerald-600 text-white text-sm hover:bg-emerald-700 disabled:opacity-50 transition"
              >
                {editSaving ? "Đang lưu…" : "Lưu thay đổi"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
