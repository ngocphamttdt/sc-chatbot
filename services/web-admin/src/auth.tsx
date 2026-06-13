import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { tokenStore, login as apiLogin } from "./api";
import type { Permission, UserType } from "./types";

const USER_KEY = "sc_admin_user";

type UserInfo = {
  userType: UserType;
  role: string;
  tenantId: string | null;
  tenantName: string | null;
  displayName: string;
  permissions: Permission[];
};

type AuthCtx = {
  token: string | null;
  isAuthed: boolean;
  userType: UserType | null;
  role: string | null;
  tenantId: string | null;
  tenantName: string | null;
  displayName: string | null;
  permissions: Permission[];
  isSuperAdmin: boolean;
  isAdmin: boolean;
  can: (p: Permission) => boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<AuthCtx | null>(null);

function loadUser(): UserInfo | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as UserInfo) : null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => tokenStore.get());
  const [user, setUser] = useState<UserInfo | null>(loadUser);

  const login = useCallback(async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    tokenStore.set(res.token);
    const info: UserInfo = {
      userType: res.user_type,
      role: res.role,
      tenantId: res.tenant_id,
      tenantName: res.tenant_name ?? null,
      displayName: res.display_name,
      // admin users có toàn quyền, tenant users dùng permissions từ role
      permissions: res.user_type === "admin" ? [] : (res.permissions ?? []),
    };
    localStorage.setItem(USER_KEY, JSON.stringify(info));
    setToken(res.token);
    setUser(info);
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === "sc_admin_token") setToken(e.newValue);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const isAdmin = user?.userType === "admin";
  const isSuperAdmin = user?.role === "super_admin";

  // admin users bypass mọi permission check
  const can = useCallback(
    (p: Permission) => isAdmin || (user?.permissions ?? []).includes(p),
    [isAdmin, user?.permissions]
  );

  return (
    <Ctx.Provider
      value={{
        token,
        isAuthed: !!token,
        userType: user?.userType ?? null,
        role: user?.role ?? null,
        tenantId: user?.tenantId ?? null,
        tenantName: user?.tenantName ?? null,
        displayName: user?.displayName ?? null,
        permissions: user?.permissions ?? [],
        isSuperAdmin,
        isAdmin,
        can,
        login,
        logout,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}
