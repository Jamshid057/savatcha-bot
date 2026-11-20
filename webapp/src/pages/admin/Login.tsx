import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { useMe } from "../../api/hooks";
import { useT } from "../../i18n";

declare global {
  interface Window {
    onTelegramAuth?: (user: Record<string, unknown>) => void;
  }
}

const BOT = (import.meta.env.VITE_BOT_USERNAME as string | undefined) ?? "";

/** Telegram Login Widget: parol saqlanmaydi, tekshiruv serverda (HMAC). */
export default function AdminLogin() {
  const { t } = useT();
  const navigate = useNavigate();
  const me = useMe();
  const holder = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    window.onTelegramAuth = (user) => {
      api("/auth/telegram-login", { method: "POST", body: user })
        .then(() => window.location.assign("/admin"))
        .catch((e: { status?: number }) =>
          setError(e.status === 403 ? t("a_login_forbidden") : t("a_login_failed")),
        );
    };
    const node = holder.current;
    if (node && BOT) {
      const script = document.createElement("script");
      script.src = "https://telegram.org/js/telegram-widget.js?22";
      script.async = true;
      script.setAttribute("data-telegram-login", BOT);
      script.setAttribute("data-size", "large");
      script.setAttribute("data-onauth", "onTelegramAuth(user)");
      script.setAttribute("data-request-access", "write");
      node.appendChild(script);
    }
    return () => {
      window.onTelegramAuth = undefined;
      if (node) node.innerHTML = "";
    };
  }, [navigate, t]);

  if (me.data?.is_admin) return <Navigate to="/admin" replace />;
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-4 rounded-2xl border border-line p-8 text-center">
        <div className="text-5xl">🛍</div>
        <h1 className="text-2xl font-extrabold">Savatcha</h1>
        <p className="text-hint">{t("a_login_hint")}</p>
        {BOT ? <div ref={holder} className="flex justify-center" /> : <p className="text-danger">VITE_BOT_USERNAME</p>}
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      </div>
    </div>
  );
}
