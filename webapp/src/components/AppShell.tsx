import { useCallback } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useMe } from "../api/hooks";
import { useT } from "../i18n";
import { isTelegram, useBackButton } from "../lib/telegram";
import { useApp } from "../store/app";
import { useEffect } from "react";
import { TabBar } from "./TabBar";
import { ErrorState, Skeleton, Toast } from "./ui";

const ROOTS = new Set(["/", "/search", "/cart", "/orders", "/profile"]);

function OpenInTelegram() {
  const { t } = useT();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="text-5xl">🛍</div>
      <h1 className="text-xl font-bold">Savatcha</h1>
      <p className="text-hint">{t("open_in_telegram")}</p>
    </div>
  );
}

/** Mijoz qobig'i: tab bar, BackButton, til sinxronlash. Telegram tashqarisida kirish yopiq. */
export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const me = useMe();
  const setLang = useApp((s) => s.setLang);
  const goBack = useCallback(() => navigate(-1), [navigate]);
  useBackButton(!ROOTS.has(location.pathname), goBack);

  useEffect(() => {
    if (me.data?.lang) setLang(me.data.lang);
  }, [me.data?.lang, setLang]);

  if (me.isPending) return <Skeleton className="m-4 h-96" />;
  if (me.isError) {
    return isTelegram() ? <ErrorState onRetry={() => void me.refetch()} /> : <OpenInTelegram />;
  }
  return (
    <div className="mx-auto max-w-2xl pb-20">
      <Toast />
      <Outlet />
      <TabBar />
    </div>
  );
}
