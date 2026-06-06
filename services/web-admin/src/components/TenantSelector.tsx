import { useEffect, useState } from "react";
import { listTenants } from "../api";
import type { Tenant } from "../types";

type Props = {
  value: string | null;
  onChange: (id: string) => void;
  allowAll?: boolean;
};

export default function TenantSelector({ value, onChange, allowAll }: Props) {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTenants()
      .then((t) => {
        setTenants(t);
        if (!value && t.length > 0 && !allowAll) onChange(t[0].tenant_id);
      })
      .catch((e) => setError(String(e.message || e)));
  }, []);

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
