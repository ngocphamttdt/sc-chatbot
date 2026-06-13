import { useEffect, useState } from "react";
import { createRole, deleteRole, listRoles, updateRole } from "../api";
import RoleBadge, { COLOR_MAP } from "../components/RoleBadge";
import { PERMISSION_GROUPS, PERMISSION_LABELS } from "../rbac";
import type { Permission, Role, RoleColor } from "../types";

const COLOR_OPTIONS: { value: RoleColor; label: string }[] = [
  { value: "emerald", label: "Xanh lá" },
  { value: "blue",    label: "Xanh dương" },
  { value: "purple",  label: "Tím" },
  { value: "amber",   label: "Vàng" },
  { value: "slate",   label: "Xám" },
  { value: "rose",    label: "Hồng" },
];

type FormState = {
  name: string;
  description: string;
  color: RoleColor;
  permissions: Permission[];
};

const emptyForm = (): FormState => ({ name: "", description: "", color: "blue", permissions: [] });

export default function Roles() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    listRoles()
      .then(setRoles)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setForm(emptyForm());
    setFormError(null);
    setEditingId(null);
    setModal("create");
  };

  const openEdit = (role: Role) => {
    setForm({ name: role.name, description: role.description, color: role.color, permissions: [...role.permissions] });
    setFormError(null);
    setEditingId(role.id);
    setModal("edit");
  };

  const closeModal = () => { setModal(null); setEditingId(null); };

  const togglePerm = (p: Permission) =>
    setForm((f) => ({
      ...f,
      permissions: f.permissions.includes(p)
        ? f.permissions.filter((x) => x !== p)
        : [...f.permissions, p],
    }));

  const save = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    setFormError(null);
    try {
      if (modal === "create") {
        const created = await createRole(form.name.trim(), form.description.trim(), form.color, form.permissions);
        setRoles((prev) => [...prev, created]);
      } else if (editingId) {
        const updated = await updateRole(editingId, {
          name: form.name.trim(),
          description: form.description.trim(),
          color: form.color,
          permissions: form.permissions,
        });
        setRoles((prev) => prev.map((r) => r.id === editingId ? updated : r));
      }
      closeModal();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Xóa role này?")) return;
    try {
      await deleteRole(id);
      setRoles((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      alert((e as Error).message);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Quản lý Roles</h1>
          <p className="text-sm text-slate-500 mt-1">Định nghĩa và phân quyền cho từng role</p>
        </div>
        <button
          onClick={openCreate}
          className="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition shadow-sm"
        >
          + Tạo role mới
        </button>
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-slate-600 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-4 py-3">Role</th>
              <th className="text-left px-4 py-3">Mô tả</th>
              <th className="text-left px-4 py-3">Quyền hạn</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={4} className="px-4 py-10 text-center text-slate-400">Đang tải…</td></tr>
            )}
            {!loading && roles.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-10 text-center text-slate-400">Chưa có role nào.</td></tr>
            )}
            {roles.map((role) => (
              <tr key={role.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <RoleBadge role={role} />
                    {role.is_system && <span className="text-xs text-slate-400">system</span>}
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs">{role.description}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {role.permissions.length === 0 ? (
                      <span className="text-xs text-slate-400">Chưa có quyền</span>
                    ) : (
                      role.permissions.map((p) => (
                        <span key={p} className="text-xs bg-gray-100 text-slate-600 px-1.5 py-0.5 rounded">
                          {PERMISSION_LABELS[p as Permission]}
                        </span>
                      ))
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-3">
                    <button onClick={() => openEdit(role)} className="text-sm text-emerald-600 hover:underline">
                      Sửa
                    </button>
                    {!role.is_system && (
                      <button onClick={() => handleDelete(role.id)} className="text-sm text-red-500 hover:underline">
                        Xóa
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4 p-6">
            <h2 className="text-lg font-semibold mb-5">
              {modal === "create" ? "Tạo role mới" : "Chỉnh sửa role"}
            </h2>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Tên role</label>
                  <input
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    placeholder="VD: Biên tập viên"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Mô tả</label>
                  <input
                    value={form.description}
                    onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    placeholder="Mô tả ngắn"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Màu sắc</label>
                <div className="flex gap-2 flex-wrap">
                  {COLOR_OPTIONS.map((c) => (
                    <button
                      key={c.value}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, color: c.value }))}
                      className={`px-3 py-1 rounded border text-xs font-medium transition ${COLOR_MAP[c.value]} ${
                        form.color === c.value ? "ring-2 ring-offset-1 ring-emerald-500" : "opacity-60 hover:opacity-100"
                      }`}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Quyền hạn</label>
                <div className="grid grid-cols-2 gap-3">
                  {PERMISSION_GROUPS.map((group) => {
                    const allChecked = group.permissions.every((p) => form.permissions.includes(p));
                    const someChecked = group.permissions.some((p) => form.permissions.includes(p));
                    const toggleGroup = () => {
                      if (allChecked) {
                        setForm((f) => ({ ...f, permissions: f.permissions.filter((p) => !group.permissions.includes(p)) }));
                      } else {
                        setForm((f) => ({ ...f, permissions: [...new Set([...f.permissions, ...group.permissions])] }));
                      }
                    };
                    return (
                      <div key={group.label} className="border border-gray-200 rounded-md overflow-hidden">
                        <div
                          className="flex items-center gap-2.5 px-3 py-2 bg-gray-50 cursor-pointer hover:bg-gray-100 transition"
                          onClick={toggleGroup}
                        >
                          <input
                            type="checkbox"
                            checked={allChecked}
                            ref={(el) => { if (el) el.indeterminate = someChecked && !allChecked; }}
                            onChange={toggleGroup}
                            onClick={(e) => e.stopPropagation()}
                            className="accent-emerald-600"
                          />
                          <span className="text-sm font-medium text-slate-700">{group.label}</span>
                        </div>
                        <div className="divide-y divide-gray-100">
                          {group.permissions.map((p) => (
                            <label key={p} className="flex items-center gap-3 px-4 py-2 cursor-pointer hover:bg-gray-50">
                              <input
                                type="checkbox"
                                checked={form.permissions.includes(p)}
                                onChange={() => togglePerm(p)}
                                className="accent-emerald-600"
                              />
                              <span className="text-sm text-slate-600">{PERMISSION_LABELS[p]}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {formError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{formError}</div>
              )}
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={closeModal}
                className="px-4 py-2 rounded border border-gray-300 text-sm text-slate-600 hover:bg-gray-50"
              >
                Hủy
              </button>
              <button
                onClick={save}
                disabled={saving || !form.name.trim()}
                className="px-4 py-2 rounded bg-emerald-600 text-white text-sm hover:bg-emerald-700 disabled:opacity-50 transition"
              >
                {saving ? "Đang lưu…" : modal === "create" ? "Tạo role" : "Lưu thay đổi"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
