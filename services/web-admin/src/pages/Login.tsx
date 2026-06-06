import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { LogoIcon } from "../components/Icons";

export default function Login() {
  const { isAuthed, login } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (isAuthed) return <Navigate to="/" replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password);
      nav("/", { replace: true });
    } catch (err) {
      setError((err as Error).message || "Đăng nhập thất bại");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white border border-gray-200 rounded-lg shadow-sm px-8 py-7"
      >
        <div className="flex items-center gap-2">
          <LogoIcon className="text-emerald-600 w-6 h-6" />
          <h1 className="text-lg font-semibold text-slate-900">SC Chatbot Admin</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">Đăng nhập để quản lý hệ thống.</p>

        <label className="block mt-6 text-sm font-medium text-slate-700">
          Tài khoản
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            autoFocus
          />
        </label>

        <label className="block mt-4 text-sm font-medium text-slate-700">
          Mật khẩu
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          />
        </label>

        {error && (
          <div className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !password}
          className="mt-6 w-full bg-emerald-600 text-white py-2 rounded-md text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition shadow-sm"
        >
          {loading ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>
      </form>
    </div>
  );
}
