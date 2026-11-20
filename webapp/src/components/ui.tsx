import { useEffect, useRef, useState, type ReactNode } from "react";
import { fetchBlobUrl } from "../api/client";
import type { OrderStatus } from "../api/types";
import { haptic, useMainButton } from "../lib/telegram";
import { useT } from "../i18n";
import { useApp } from "../store/app";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-surface ${className}`} />;
}

export function ProductGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {Array.from({ length: 6 }, (_, i) => (
        <Skeleton key={i} className="h-52" />
      ))}
    </div>
  );
}

export function ErrorState({ onRetry }: { onRetry: () => void }) {
  const { t } = useT();
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <div className="text-4xl">😕</div>
      <p className="text-hint">{t("err_generic")}</p>
      <button className="btn" onClick={onRetry}>
        {t("retry")}
      </button>
    </div>
  );
}

export function Empty({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-16 text-center text-hint">
      <div className="text-5xl">{icon}</div>
      <p>{text}</p>
    </div>
  );
}

export function QuantityStepper({
  value,
  onChange,
  min = 0,
  max = 99,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
}) {
  const step = (d: number) => {
    const next = Math.min(max, Math.max(min, value + d));
    if (next !== value) {
      haptic.select();
      onChange(next);
    }
  };
  return (
    <div className="inline-flex items-center rounded-xl bg-surface">
      <button className="h-9 w-9 text-lg font-bold" onClick={() => step(-1)} aria-label="−">
        −
      </button>
      <span className="min-w-8 text-center text-sm font-semibold">{value}</span>
      <button className="h-9 w-9 text-lg font-bold" onClick={() => step(1)} aria-label="+">
        +
      </button>
    </div>
  );
}

const STATUS_STYLE: Record<OrderStatus, string> = {
  new: "bg-blue-500/15 text-blue-600 dark:text-blue-300",
  accepted: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
  delivering: "bg-purple-500/15 text-purple-600 dark:text-purple-300",
  done: "bg-green-500/15 text-green-600 dark:text-green-300",
  cancelled: "bg-red-500/15 text-red-600 dark:text-red-300",
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  const { t } = useT();
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_STYLE[status]}`}>
      {t(`status_${status}`)}
    </span>
  );
}

/** Telegram ichida MainButton, tashqarisida pastga mahkamlangan oddiy tugma. */
export function MainAction({
  text,
  onClick,
  disabled,
  loading,
  visible = true,
}: {
  text: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  visible?: boolean;
}) {
  const native = useMainButton({ text, onClick, disabled, loading, visible });
  if (native || !visible) return null;
  return (
    <div className="no-print fixed inset-x-0 bottom-16 z-20 bg-bg/90 p-3 backdrop-blur">
      <button className="btn w-full" onClick={onClick} disabled={disabled || loading}>
        {loading ? "…" : text}
      </button>
    </div>
  );
}

export function Toast() {
  const toast = useApp((s) => s.toast);
  if (!toast) return null;
  return (
    <div
      key={toast.id}
      role="status"
      className={`fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-xl px-4 py-2 text-sm font-medium text-white shadow-lg ${
        toast.kind === "ok" ? "bg-ok" : "bg-danger"
      }`}
    >
      {toast.text}
    </div>
  );
}

/** Lazy-loading rasm; yuklanmasa yoki yo'q bo'lsa belgi ko'rsatiladi. */
export function ProductImage({ src, alt, className = "" }: { src: string | null; alt: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <div className={`flex items-center justify-center bg-surface text-4xl ${className}`}>🛍</div>
    );
  }
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`object-cover ${className}`}
    />
  );
}

/** Auth sarlavhasi kerak bo'lgan rasm (chek). */
export function AuthedImage({ path, alt, className = "" }: { path: string; alt: string; className?: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let revoked: string | null = null;
    let cancelled = false;
    fetchBlobUrl(path)
      .then((u) => {
        if (cancelled) URL.revokeObjectURL(u);
        else {
          revoked = u;
          setUrl(u);
        }
      })
      .catch(() => setFailed(true));
    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [path]);
  if (failed) return null;
  if (!url) return <Skeleton className={`h-40 ${className}`} />;
  return <img src={url} alt={alt} className={className} />;
}

export function InfiniteSentinel({ onVisible, enabled }: { onVisible: () => void; enabled: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!enabled || !ref.current) return;
    const obs = new IntersectionObserver((e) => e[0]?.isIntersecting && onVisible(), {
      rootMargin: "200px",
    });
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, [enabled, onVisible]);
  return <div ref={ref} className="h-1" />;
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-hint">{title}</h2>
      {children}
    </section>
  );
}
