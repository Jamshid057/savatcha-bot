import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { api, setUnauthorizedHandler } from "../../api/client";
import { useMe } from "../../api/hooks";
import type { Order, Page } from "../../api/types";
import { useT } from "../../i18n";
import { isTelegram, useBackButton } from "../../lib/telegram";
import { useApp } from "../../store/app";
import { Skeleton, Toast } from "../ui";

const NAV = [
  { to: "/admin", end: true, icon: "📊", key: "a_nav_dashboard" },
  { to: "/admin/orders", end: false, icon: "🧾", key: "a_nav_orders" },
  { to: "/admin/products", end: false, icon: "📦", key: "a_nav_products" },
  { to: "/admin/categories", end: false, icon: "🗂", key: "a_nav_categories" },
  { to: "/admin/customers", end: false, icon: "👥", key: "a_nav_customers" },
  { to: "/admin/reports", end: false, icon: "📈", key: "a_nav_reports" },
  { to: "/admin/audit", end: false, icon: "📜", key: "a_nav_audit" },
  { to: "/admin/settings", end: false, icon: "⚙️", key: "a_nav_settings" },
];

const THEME_KEY = "savatcha.theme";

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  useEffect(() => {
    if (isTelegram()) return; // Mini App ichida Telegram temasi
    try {
      const saved = localStorage.getItem(THEME_KEY);
      const wantDark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
      document.documentElement.classList.toggle("dark", wantDark);
      setDark(wantDark);
    } catch {
      /* localStorage mavjud emas */
    }
  }, []);
  const toggle = () => {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    setDark(next);
    try {
      localStorage.setItem(THEME_KEY, next ? "dark" : "light");
    } catch {
      /* e'tiborsiz */
    }
  };
  return { dark, toggle };
}

/** Yangi buyurtma kelganda 30 soniyada bir so'rov bilan toast ko'rsatadi. */
function usePendingOrders(): number {
  const qc = useQueryClient();
  const { t } = useT();
  const showToast = useApp((s) => s.showToast);
  const last = useRef<number | null>(null);
  const query = useQuery({
    queryKey: ["admin", "pending"],
    queryFn: () => api<Page<Order>>("/admin/orders", { query: { status: "new", per_page: 1 } }),
    refetchInterval: 30_000,
  });
  const total = query.data?.total;
  useEffect(() => {
    if (total === undefined) return;
    if (last.current !== null && total > last.current) {
      showToast(t("a_new_order_toast"));
      void qc.invalidateQueries({ queryKey: ["admin"] });
      void qc.invalidateQueries({ queryKey: ["stat"] });
    }
    last.current = total;
  }, [total, qc, showToast, t]);
  return total ?? 0;
}

function Shell() {
  const { t } = useT();
  const navigate = useNavigate();
  const { dark, toggle } = useTheme();
  const pending = usePendingOrders();
  const [search, setSearch] = useState("");
  useBackButton(false, () => undefined);

  const logout = async () => {
    try {
      await api<void>("/auth/logout", { method: "POST" });
    } finally {
      window.location.assign("/admin/login");
    }
  };

  return (
    <div className="min-h-screen lg:flex">
      <Toast />
      <aside className="no-print hidden w-60 shrink-0 border-r border-line bg-surface/50 p-4 lg:block">
        <div className="mb-6 text-xl font-extrabold">🛍 Savatcha</div>
        <nav className="space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex items-center justify-between rounded-xl px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-accent text-accent-text" : "hover:bg-surface"
                }`
              }
            >
              <span>
                {n.icon} {t(n.key)}
              </span>
              {n.to === "/admin/orders" && pending > 0 && (
                <span className="rounded-full bg-danger px-2 text-xs font-bold text-white">{pending}</span>
              )}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="no-print sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-bg/90 px-4 py-3 backdrop-blur">
          <form
            className="flex-1"
            onSubmit={(e) => {
              e.preventDefault();
              navigate(`/admin/orders?q=${encodeURIComponent(search.trim())}`);
            }}
          >
            <input
              className="input max-w-md"
              type="search"
              placeholder={t("a_global_search")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </form>
          {isTelegram() ? (
            <Link to="/" className="btn-secondary px-3 py-2">
              🛍
            </Link>
          ) : (
            <>
              <button className="btn-secondary px-3 py-2" onClick={toggle} aria-label="theme">
                {dark ? "☀️" : "🌙"}
              </button>
              <button className="btn-secondary px-3 py-2" onClick={() => void logout()}>
                {t("a_logout")}
              </button>
            </>
          )}
        </header>
        <nav className="no-print flex gap-1 overflow-x-auto border-b border-line px-2 py-2 lg:hidden [scrollbar-width:none]">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `shrink-0 rounded-full px-3 py-1.5 text-sm ${isActive ? "bg-accent text-accent-text" : "bg-surface"}`
              }
            >
              {n.icon} {t(n.key)}
            </NavLink>
          ))}
        </nav>
        <main className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

/** Admin qobig'i: Telegram (initData) yoki brauzer sessiya cookie si bilan kiradi. */
export function AdminLayout() {
  const me = useMe();
  const navigate = useNavigate();
  useEffect(() => {
    setUnauthorizedHandler(() => navigate("/admin/login", { replace: true }));
    return () => setUnauthorizedHandler(null);
  }, [navigate]);

  if (me.isPending) return <Skeleton className="m-6 h-96" />;
  if (me.isError) return <Navigate to="/admin/login" replace />;
  if (!me.data.is_admin) return <Navigate to="/" replace />;
  return <Shell />;
}
