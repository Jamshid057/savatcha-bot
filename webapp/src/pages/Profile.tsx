import { useEffect, useState } from "react";
import { errorText, useMe, usePatchMe } from "../api/hooks";
import { ErrorState, Skeleton } from "../components/ui";
import { useT } from "../i18n";
import { normalizePhone, type Lang } from "../lib/format";
import { haptic } from "../lib/telegram";
import { useApp } from "../store/app";

export default function Profile() {
  const { t, lang } = useT();
  const me = useMe();
  const patch = usePatchMe();
  const showToast = useApp((s) => s.showToast);
  const [phone, setPhone] = useState("");
  useEffect(() => setPhone(me.data?.phone ?? ""), [me.data?.phone]);

  if (me.isPending) return <Skeleton className="m-4 h-48" />;
  if (me.isError) return <ErrorState onRetry={() => void me.refetch()} />;
  const user = me.data;

  const setLanguage = (l: Lang) => {
    haptic.select();
    patch.mutate({ lang: l });
  };
  const savePhone = () => {
    if (!normalizePhone(phone)) {
      showToast(t("err_invalid_phone"), "error");
      return;
    }
    patch.mutate(
      { phone },
      { onSuccess: () => showToast(t("saved")), onError: (e) => showToast(errorText(e, t), "error") },
    );
  };

  return (
    <div className="space-y-5 p-4">
      <div className="card">
        <div className="text-lg font-bold">{user.full_name}</div>
        {user.username && <div className="text-sm text-hint">@{user.username}</div>}
      </div>
      <div className="space-y-2">
        <h2 className="text-sm font-semibold uppercase text-hint">{t("language")}</h2>
        <div className="grid grid-cols-2 gap-2">
          {(["uz", "ru"] as Lang[]).map((l) => (
            <button key={l} className={lang === l ? "btn" : "btn-secondary"} onClick={() => setLanguage(l)}>
              {l === "uz" ? "🇺🇿 O'zbekcha" : "🇷🇺 Русский"}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        <h2 className="text-sm font-semibold uppercase text-hint">{t("field_phone")}</h2>
        <input className="input" type="tel" inputMode="tel" placeholder="+998 90 123 45 67" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <button className="btn w-full" onClick={savePhone} disabled={patch.isPending}>
          {t("save")}
        </button>
      </div>
    </div>
  );
}
