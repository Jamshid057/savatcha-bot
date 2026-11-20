import { NavLink } from "react-router-dom";
import { useCart } from "../api/hooks";
import { useT } from "../i18n";
import { cartCount } from "../lib/cart";

const TABS = [
  { to: "/", icon: "🏠", key: "tab_home", end: true },
  { to: "/search", icon: "🔎", key: "tab_search", end: false },
  { to: "/cart", icon: "🛒", key: "tab_cart", end: false },
  { to: "/orders", icon: "📦", key: "tab_orders", end: false },
  { to: "/profile", icon: "👤", key: "tab_profile", end: false },
];

export function TabBar() {
  const { t } = useT();
  const count = cartCount(useCart().data);
  return (
    <nav className="no-print fixed inset-x-0 bottom-0 z-30 border-t border-line bg-bg pb-[env(safe-area-inset-bottom)]">
      <ul className="mx-auto flex max-w-2xl">
        {TABS.map((tab) => (
          <li key={tab.to} className="flex-1">
            <NavLink
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                `relative flex flex-col items-center gap-0.5 py-2 text-[11px] ${
                  isActive ? "font-semibold text-accent" : "text-hint"
                }`
              }
            >
              <span className="relative text-xl leading-none">
                {tab.icon}
                {tab.to === "/cart" && count > 0 && (
                  <span className="absolute -right-3 -top-2 min-w-4 rounded-full bg-danger px-1 text-center text-[10px] font-bold leading-4 text-white">
                    {count}
                  </span>
                )}
              </span>
              {t(tab.key)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
