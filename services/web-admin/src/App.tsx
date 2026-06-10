import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Protected from "./components/Protected";
import Conversations from "./pages/Conversations";
import Documents from "./pages/Documents";
import Login from "./pages/Login";
import Prompt from "./pages/Prompt";
import Settings from "./pages/Settings";
import Stats from "./pages/Stats";

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
        <Route index element={<Navigate to="/stats" replace />} />
        <Route path="stats" element={<Stats />} />
        <Route path="documents" element={<Documents />} />
        <Route path="prompt" element={<Prompt />} />
        <Route path="settings" element={<Settings />} />
        <Route path="conversations" element={<Conversations />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
