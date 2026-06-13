import { useEffect, useState } from "react";
import { listTenants } from "../api";
import { useAuth } from "../auth";
import type { Tenant } from "../types";

type Props = {
  value: string | null;
  onChange: (id: string) => void;
  allowAll?: boolean;
};

export default function TenantSelector({ value, onChange, allowAll }: Props) {
  const { isAdmin, tenantId: authTenantId } = useAuth();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAdmin) {
      // Tenant users: auto-set to their own tenant, no API call needed
      if (authTenantId && !value) onChange(authTenantId);
      return;
    }
    listTenants()
      .then((t) => {
        setTenants(t);
        if (!value && t.length > 0 && !allowAll) onChange(t[0].tenant_id);
      })
      .catch((e) => setError(String(e.message || e)));
  }, [isAdmin, authTenantId]);

  // Tenant users: show their tenant as read-only, no dropdown
  if (!isAdmin) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-500">Tenant:</span>
        <span className="text-sm font-medium text-slate-700">{authTenantId ?? "—"}</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm text-slate-600">Tenant:</label>
      <select
        className="border border-gray-300 rounded px-2 py-1 text-sm bg-white"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
      >
        {allowAll && <option value="">(Tất cả)</option>}
        {tenants.map((t) => (
          <option key={t.tenant_id} value={t.tenant_id}>
            {t.name} — {t.tenant_id}
          </option>
        ))}
      </select>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
